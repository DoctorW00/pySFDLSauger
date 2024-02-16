import sys, os, argparse, threading, time, socks, re, requests, tempfile, base64, hashlib, tqdm, subprocess, shutil
from pathlib import Path
from socket import error as socket_error
from ftplib import FTP, error_temp, error_perm, error_proto, error_reply, Error
from urllib.parse import unquote
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from math import log2
import xml.etree.ElementTree as ET
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

__version__ = "2.1.0"
__printdebug__ = False
__required_packages__ = ['tqdm', 'requests', 'cryptography', 'socks', 'sockshandler', 'urllib3', 'watchdog']
__download_running__ = False
__monitor_mode__ = False
__use_unrar__ = None

class Proxy:
    def __init__(self, host, port, username=None, password=None):
        self.proxy = socks.socksocket()
        self.proxy.set_proxy(socks.SOCKS5, host, port, username=username, password=password)

    def connect(self, target_host, target_port):
        self.proxy.connect((target_host, target_port))

    def close(self):
        self.proxy.close()

class FTPList:
    def __init__(self, ftp_host=None, ftp_port=21, ftp_user="anonymous", ftp_pass="anonymous@sauger.local", ftp_path=None, proxy=None):
        self.ftp = None
        self.files = []
        self.files_index = 0
        self.ftp_host = ftp_host
        self.ftp_port = ftp_port
        self.ftp_user = ftp_user
        self.ftp_pass = ftp_pass
        self.ftp_path = ftp_path
        self.proxy = proxy

    def get_final_destination(self, ftp_full_path):
        destination_path = None
        destination_file = None
        destination_file = ftp_full_path.rsplit('/', 1)[-1]

        if self.destination_path is not None and self.release_name is not None and destination_file is not None:
            destination_path = self.destination_path + "/" + self.release_name + "/" + destination_file
            destination_path = destination_path.replace("//", "/")
            return destination_path
        else:
            return None

    def file_by_index(self, index):
        if 0 <= index < len(self.files):
            return self.files[index]
        else:
            return None

    def ftp_login(self):
        __download_running__ = True
        try:
            self.ftp = FTP()
            if self.proxy is not None:
                self.ftp.sock = self.proxy
            self.ftp.connect(self.ftp_host, self.ftp_port)
            self.ftp.login(self.ftp_user, self.ftp_pass)
            self.ftp.set_pasv(True)
            self.ftp.encoding = "utf-8"
        except (error_temp, error_perm, error_proto, error_reply, Error, socket_error) as e:
            print(f" \033[91;1mFTP Connection Error: {e}\033[0m")
            self.close()
            sys.exit(1)

    def list_files(self, path="."):
        if self.ftp is None:
            self.ftp_login()
            return

        full_path = f"{self.ftp_path}/{path}" if path != "." else self.ftp_path

        try:
            self.ftp.cwd(full_path)
        except Exception:
            return
        
        files = {}
        
        # get some workaround going to get better results from more ftp servers
        # try mlsd command
        try:
            files_info = self.ftp.mlsd(facts=["type", "size"])
            if files_info is not None:
                files = sorted(files_info)
        except Exception as e:
            # try nlst + size command
            file_list = self.ftp.nlst()
            self.ftp.sendcmd("TYPE I")
            for file_name in file_list:
                try:
                    size = self.ftp.size(file_name)
                    files[file_name] = {'type': 'file', 'size': size}
                except Exception as e:
                    files[file_name] = {'type': 'file', 'size': None}
            files = sorted(files.items(), key=lambda x: x[1]['size'])

        for item, data in files:
            if data["type"] == "file":
                size = int(data["size"])
                clean_ftp_path = self.ftp_path.rstrip("/")
                rec_path = path.lstrip("./")
                clean_item = item.lstrip("./")

                final_full_file_path = None

                if rec_path == ".":
                    final_full_file_path = clean_ftp_path + "/" + clean_item
                else:
                    final_full_file_path = clean_ftp_path + "/" + rec_path + "/" + clean_item
                    
                final_full_file_path = final_full_file_path.replace("//", "/")
                self.files.append((final_full_file_path, size))

        for item in files:
            try:
                self.list_files(f"{path}/{item}")
            except Exception as e:
                pass
        
        if self.files is not None:
            self.close()
            
        return self.files

    def close(self):
        if self.ftp is not None:
            try:
                self.ftp.quit()
                if self.proxy is not None:
                    self.proxy.close()
                if __printdebug__: print(f"FTPList: FTP Connection Closed!")
                __download_running__ = False
            except AttributeError:
                pass
            finally:
                self.ftp = None

class FTPDownloader:
    def __init__(self, ftp_host, ftp_port=21, ftp_user="anonymous", ftp_pass="anonymous@sauger.local", download_folder=None, max_threads=10, release_name=None, proxy=None, sfdl_file=None):
        self.ftp_sessions = {}
        self.ftp_lock = threading.Lock()
        self.ftp_host = ftp_host
        self.ftp_port = ftp_port
        self.ftp_user = ftp_user
        self.ftp_pass = ftp_pass
        self.download_folder = download_folder
        self.max_threads = int(max_threads)
        self.thread_semaphore = threading.Semaphore(self.max_threads)
        self.release_name = release_name
        self.proxy = proxy
        self.sfdl_file = sfdl_file
        self.bar = None # main progress for the whole download
        self.bars = []  # progressbars for files
        self.bars_lock = threading.Lock()
        self.bars_count = 0
        self.start_time = 0
        self.done_time = 0
        self.b2h = bytes2human
        self.local_download_path = None

    def write_speedreport(self, path, line1, line2):
        speedreport = path + '/speedreport.txt'
        try:
            with open(speedreport, 'w') as file:
                file.write(f'Speedreport for [B]{line1}[/B]\n')
                file.write('[HR][/HR]\n')
                file.write(f'{line2}\n')
                file.write(f'Thanks! :mx1_7:\n')
                file.write(f'[URL="https://mlcboard.com/forum/showthread.php?598380"][SIZE=1][I]pySFDLSauger ({__version__})[/I][/SIZE][/URL] \n')
            print(f' \033[93;1mSpeedreport created:\033[0m \033[94;1m{speedreport}\033[0m')
        except Exception as e:
            print(f" \033[91;1mError creating speedreport file: {speedreport} {e}\033[0m")

    def ensure_directory_exists(self, file_path):
        directory = os.path.dirname(file_path)
        if not os.path.exists(directory):
            os.makedirs(directory)

    def move_file(self, file_path, destination_path):
        try:
            dest_path = os.path.normpath(destination_path + "/" + self.release_name)
            if __printdebug__:
                print(f" \033[93;1mMoving:\033[0m \033[92;1m{file_path}\033[0m \033[93;1mto\033[0m \033[92;1m{dest_path}\033[0m")
            else:
                print(f" \033[93;1mMoving SFDL to download path!\033[0m")
            shutil.move(file_path, dest_path)
        except Exception as e:
            print(f" \033[91;1mError: Can't move SFDL to download folder: {e}\033[0m")

    def get_release_from_path(self, path):
        release = None
        last_slash_index = path.rfind('/')
        if last_slash_index != -1:
            path = path[:last_slash_index]
            new_last_slash_index = path.rfind('/')
            if new_last_slash_index != -1:
                release = path[new_last_slash_index + 1:]
        return release
    
    def return_local_file_path(self, local_filepath, remote_path):
        if self.download_folder is None:
            local_filepath = os.path.join(self.download_folder, local_filepath)
        else:
            local_filepath = self.download_folder
        
        release = None
        if self.release_name is not None:
            release = self.release_name
        else:
            release = self.get_release_from_path(remote_path)
        
        index = remote_path.find(release)
        
        subdir = None
        if index != -1:
            subdir = remote_path[index + len(release):]
            local_filepath = local_filepath + "/" + release + "/" + subdir
        else:
            local_filepath = local_filepath + "/" + release
        self.local_download_path = os.path.normpath(os.path.dirname(local_filepath.replace("//", "/")))
        return local_filepath.replace("//", "/")
    
    def calculate_download_speed(self, file_size, elapsed_time_seconds):
        speed_bytes_per_sec = file_size / elapsed_time_seconds
        ergebnis = self.b2h(speed_bytes_per_sec, 1000)
        return ergebnis
    
    def seconds_to_readable_time(self, seconds):
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)
        time_parts = []
        if days == 1:
            time_parts.append("1 Day")
        elif days > 1:
            time_parts.append(f"{int(days)} Days")
        if hours == 1:
            time_parts.append("1 Hour")
        elif hours > 1:
            time_parts.append(f"{int(hours)} Hours")
        if minutes == 1:
            time_parts.append("1 Minute")
        elif minutes > 1:
            time_parts.append(f"{int(minutes)} Minutes")
        if seconds == 1:
            time_parts.append("1 Second")
        elif seconds > 1 or not time_parts:
            time_parts.append(f"{int(seconds)} Seconds")
        return ", ".join(time_parts)

    def connect(self):
        with self.ftp_lock:
            try:
                ftp = FTP()
                if self.proxy is not None:
                    ftp.sock = self.proxy
                ftp.connect(self.ftp_host, self.ftp_port)
                ftp.login(self.ftp_user, self.ftp_pass)
                ftp.set_pasv(True)
                ftp.encoding = "utf-8"
                if ftp is not None:
                    return ftp
                else:
                    return None
            except (error_temp, error_perm, error_proto, error_reply, Error, socket_error) as e:
                error_message = str(e).lower().strip()
                if error_message.startswith("553") or error_message.startswith("530"):
                    time.sleep(10)
                    return self.connect()
                else:
                    print(f" \033[91;1m[1] FTP Connection Error: {e}\033[0m")
                    return None
    
    def get_ftp_session(self):
        try:
            current_thread = threading.current_thread()
            if current_thread not in self.ftp_sessions or not self.ftp_sessions[current_thread].sock:
                new_session = self.connect()
                if new_session is not None:
                    self.ftp_sessions[current_thread] = new_session
            return self.ftp_sessions[current_thread]
        except (error_temp, error_perm, error_proto, error_reply, Error, socket_error) as e:
            if __printdebug__: print(f" \033[91;1m[1] FTP Connection Error in get_ftp_session: {e}\033[0m")
            return None
        except EOFError as eof_error:
            if __printdebug__: print(f" \033[91;1m[1] EOFError in get_ftp_session: {eof_error}\033[0m")
            return None
    
    def download_multiple_files(self, file_list):
        __download_running__ = True
        self.start_time = time.time()
        
        total_size = sum(file_size for _, file_size in file_list)
        total_files = len(file_list)
        
        self.bar = tqdm.tqdm(total=total_size, unit_scale=True, dynamic_ncols=True, desc=f' \033[91;1m{self.release_name}\033[0m', miniters=1, file=sys.stdout, leave=True, colour="green")

        threads = []
        for remote_path, file_size in file_list:
            local_file = os.path.basename(remote_path)
            thread = threading.Thread(target=self.download_in_thread, args=(remote_path, local_file, file_size, total_files))
            threads.append(thread)
            thread.start()
            time.sleep(0.1)

        for thread in threads:
            thread.join()
            
        for bar in self.bars:
            bar.close()
        
        self.bar.close()
        
        # move sfdl to download folder
        self.move_file(self.sfdl_file, self.download_folder)
        # get download time
        self.done_time = time.time() - self.start_time
        speed = self.calculate_download_speed(total_size, self.done_time)
        elapsed_time = self.seconds_to_readable_time(self.done_time)
        
        print(f" \033[93;1mDownload completed in\033[0m \033[92;1m{elapsed_time} ({speed}/s)\033[0m")
        
        # create speedreport in download folder
        self.write_speedreport(self.local_download_path, self.release_name, f'Downloaded {total_files} files in {elapsed_time} ({speed}/s)')
        
        # use UnRAR to rextract RAR archives
        if __use_unrar__ is not None:
            rar_extractor = RarExtractor(self.local_download_path, self.local_download_path, password='')
            success = rar_extractor.extract_rar()
            if success:
                print(f" \033[93;1mUnRAR ALL OK!\033[0m")
            else:
                print(f" \033[91;1mUnRAR error!\033[0m")
        
        __download_running__ = False
        
        # start next download if there is one
        if __monitor_mode__ is True:
            time.sleep(5)
            nextDownload = WatcherHandler
            nextDownload.update_file_paths

    def download_in_thread(self, remote_path, local_file, file_size, total_files):
        ftp = None
        e = None
        try:
            try:
                ftp = self.get_ftp_session()
            except (error_temp, error_perm, error_proto, error_reply, Error, socket_error) as e:
                if __printdebug__: print(f" \033[91;1mDownload Thread Error: {e}\033[0m")
            
            if ftp is not None:
                with self.thread_semaphore:
                    newBarIndex = self.bars_count
                    self.bars_count += 1
                    self.download_with_progress(ftp, remote_path, local_file, file_size, total_files, newBarIndex)
            else:
                if __printdebug__: print(f" \033[91;1m[1] FTP Connection Error: {e}\033[0m")
        except threading.ThreadError as te:
            if __printdebug__: print(f" \033[91;1mDownload Thread Error: {te}\033[0m")
        finally:
            if ftp is not None:
                if __printdebug__: print(f" \033[93;1mDownloaded\033[0m \033[92;1m{local_file}\033[0m \033[93;1msuccessfully!\033[0m")
                ftp.close()
            # remove file progressbar
            if newBarIndex < len(self.bars):
                self.bars[newBarIndex].clear()
                self.bars[newBarIndex].close()
            else:
                self.bars[0].clear()
                self.bars[0].close()

    def download_with_progress(self, ftp, remote_path, local_file, file_size, total_files, newBarIndex):
        local_filepath = os.path.join(self.download_folder, local_file)
        if ftp is None:
            ftp = self.connect()
        
        if ftp is not None:
            try:
                local_filename = os.path.basename(local_filepath)
                
                if newBarIndex < len(self.bars):
                    self.bars[newBarIndex] = tqdm.tqdm(total=file_size, unit_scale=True, desc=f' \033[93;1mLoading\033[0m \033[92;1m{local_filename}\033[0m', miniters=1, file=sys.stdout, leave=False, colour="yellow")
                else:
                    self.bars.append(tqdm.tqdm(total=file_size, unit_scale=True, desc=f' \033[93;1mLoading\033[0m \033[92;1m{local_filename}\033[0m', miniters=1, file=sys.stdout, leave=False, colour="yellow"))
                
                # check if we got a partial file and continue download if so
                if os.path.exists(local_filepath):
                    local_file_size = os.path.getsize(local_filepath)
                    ftp.sendcmd(f"REST {local_file_size}")
                
                ftp.retrbinary(f"RETR {remote_path}", lambda data: self.write_with_progress(data, local_filepath, remote_path, file_size, total_files, newBarIndex), blocksize=1024)
                
            except (error_temp, error_perm, error_proto, error_reply, Error, socket_error) as e:
                # retry if server responds max connections reached
                error_message = str(e).lower().strip()
                if error_message.startswith("553") or error_message.startswith("530"):
                    if ftp is not None:
                        if __printdebug__: print("[2] Download: Closing connection!")
                        ftp.close()
                    if __printdebug__: print("[2] Download: Server maximum connections reached ... retry in 10 ...")
                    time.sleep(10)
                    self.download_in_thread(remote_path, local_file, file_size, total_files)
                    sys.exit() # end current thread
                else:
                    print(f" \033[91;1m[2] FTP Connection Error: {e}\033[0m")
            finally:
                if ftp is not None:
                    ftp.close()

    def write_with_progress(self, data, local_filepath, remote_path, file_size, total_files, newBarIndex):
        
        local_filepath = self.return_local_file_path(local_filepath, remote_path)
        self.ensure_directory_exists(local_filepath)
        
        try:
            with open(local_filepath, 'ab') as local_file:
                local_file.write(data)
                if newBarIndex < len(self.bars):
                    self.bars[newBarIndex].update(len(data))
                    self.bar.update(len(data))
        except Exception as e:
            print(f" \033[91;1mError can't write file: {e}\033[0m")

class WatcherHandler(FileSystemEventHandler):
    sfdl_files = []

    def __init__(self, directory_to_watch, password, destination, threads):
        super().__init__()
        self.directory_to_watch = directory_to_watch
        self.password = password
        self.destination = destination
        self.threads = threads
        self.file_paths = WatcherHandler.sfdl_files
        self.initialize_existing_files()
        
    def initialize_existing_files(self):
        for root, dirs, files in os.walk(self.directory_to_watch):
            for file in files:
                file_path = os.path.join(root, file)
                if file_path.lower().endswith(".sfdl") and file_path not in self.file_paths and os.path.exists(file_path):
                    if os.path.exists(file_path):
                        if __printdebug__: print(f" SFDL found: {file_path}")
                        self.file_paths.append(file_path)
                        self.update_file_paths()

    def on_created(self, event):
        if event.is_directory:
            return
        file_path = event.src_path
        if file_path.lower().endswith(".sfdl") and file_path not in self.file_paths and os.path.exists(file_path):
            if __printdebug__: print(f" New SFDL found: {file_path}")
            self.file_paths.append(file_path)
            self.update_file_paths()

    def on_modified(self, event):
        if not event.is_directory:
            file_path = event.src_path
            if file_path.lower().endswith(".sfdl") and file_path not in self.file_paths and os.path.exists(file_path):
                if __printdebug__: print(f" Existing SFDL found: {file_path}")
                self.file_paths.append(file_path)
                self.update_file_paths()
                
    def on_deleted(self, event):
        if not event.is_directory:
            file_path = event.src_path
            if file_path.lower().endswith(".sfdl") and file_path in self.file_paths:
                if __printdebug__: print(f" SFDL {file_path} got deleted!")
                self.file_paths.remove(file_path)
                self.update_file_paths()

    def update_file_paths(self):
        updated_file_paths = []
        for file_path in self.file_paths:
            try:
                os.path.getmtime(file_path)
                if os.path.exists(file_path):
                    updated_file_paths.append(file_path)
            except (OSError, FileNotFoundError):
                if __printdebug__: print(f" SFDL {file_path} got deleted or is no longer accessible!")
                
        updated_file_paths = sorted(updated_file_paths, key=os.path.getmtime, reverse=False)
        self.file_paths = updated_file_paths
        if __printdebug__: print(self.file_paths)
        if len(self.file_paths):
            if __download_running__ is False:
                printBanner()
                self.startDownload(self.file_paths[0])
    
    # start new download
    def startDownload(self, sfdl_file):
        sfdl = getSFDL(sfdl_file)
        sfdl_data = []
        sfdl_data = readSFDL(sfdl, self.password)
        release_name, ftp_host, ftp_port, ftp_user, ftp_pass, ftp_path = (None, None, None, None, None, None)
        if sfdl_data is not None:
            release_name = sfdl_data['release_name']
            ftp_host = sfdl_data['ftp_host']
            ftp_port = sfdl_data['ftp_port']
            ftp_user = sfdl_data['ftp_user']
            ftp_pass = sfdl_data['ftp_pass']
            ftp_path = sfdl_data['ftp_path']
        else:
            print(f" \033[91;1mError: Can't read data from {sfdl_file}!\033[0m")
            
        if all(variable is not None for variable in [ftp_host, ftp_port, ftp_path]):
            main(ftp_host, int(ftp_port), ftp_user, ftp_pass, ftp_path, self.destination, int(self.threads), release_name, proxy, sfdl_file)
        else:
            print(f" \033[91;1mError: Missing FTP data from SFDL file!\033[0m")
            # rename sfdl file to sfdl.err to exclude it from downloads
            try:
                os.rename(sfdl_file, sfdl_file + ".err")
                if __printdebug__: print(f" \033[91;1mError: Renaming {sfdl_file} to {sfdl_file}.err!\033[0m")
            except FileNotFoundError:
                pass
            except Exception as e:
                pass

class FileWatcher:
    def __init__(self, directory_to_watch, password, destination, threads):
        self.handler = WatcherHandler(directory_to_watch, password, destination, threads)
        self.observer = Observer()
        self.observer_thread = None

    def start_watching(self):
        self.observer.schedule(self.handler, path=self.handler.directory_to_watch, recursive=True)
        self.observer.start()
        
        print(f" \033[93;1mpySFDLSauger watchdog is now running, automatic download service ready!\033[0m")
        print(f" \033[93;1mAdd new SFDL files in\033[0m \033[94;1m{self.handler.directory_to_watch}\033[0m \033[93;1mfor automatic downloads!\033[0m")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
            self.observer.join()

class RarExtractor:
    def __init__(self, rar_path, extract_path, password=None):
        self.rar_path = rar_path
        self.extract_path = extract_path
        self.password = password
        self.progress_regex = re.compile(r'(\d+)%')
        self.file_info_regex = re.compile(r'Extracting from (.+)')

    def find_all_rar_files(self, folder_path):
        rar_regex = re.compile(r'^(.*?)(?:\.part\d*\.rar|\.r\d{2,}|\.[s-z]\d{2,}|\d+\.rar)$', re.IGNORECASE)
        rar_files = [file for file in os.listdir(folder_path) if rar_regex.match(file)]
        return [os.path.join(folder_path, file) for file in rar_files]

    def find_rar_file(self, folder_path):
        rar_regex = re.compile(r'^(.*?)(?:\.part\d*\.rar|\.rar)$', re.IGNORECASE)
        rar_files = [file for file in os.listdir(folder_path) if rar_regex.match(file)]
        
        if rar_files:
            rar_files.sort()
            return os.path.join(folder_path, rar_files[0])
        else:
            return None

    def delete_rar_files(self, rar_files):
        for rar_file in tqdm.tqdm(rar_files, desc=" \033[93;1mRemoving RAR files ...\033[0m", unit="file", colour="magenta"):
            try:
                os.remove(rar_file)
                if __printdebug__: print(f" \033[93;1mUnRAR removing: {rar_file}\033[0m")
            except Exception as e:
                print(f" \033[91;1mUnRAR error: Unable to remove: {rar_file}: {e}\033[0m")

    def is_unrar_available(self):
        try:
            subprocess.run(['unrar'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return True
        except FileNotFoundError:
            return False
        except subprocess.CalledProcessError:
            return False

    def extract_rar(self):
        allRARFiles = self.find_all_rar_files(self.rar_path)
        firstRAR = self.find_rar_file(self.rar_path)
        if firstRAR is None:
            print(f" \033[91;1mUnRAR error: No RAR file found in {self.rar_path}\033[0m")
            return False
        
        try:
            if not self.is_unrar_available():
                raise Exception(f" \033[91;1mUnRAR error: Can\'t find UnRAR executable! Please install UnRAR first!\033[0m")

            command = ['unrar', 'x', '-o+', firstRAR, self.extract_path]
            if self.password:
                command.extend(['-p' + self.password])

            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            
            with tqdm.tqdm(total=100, dynamic_ncols=True, desc=f' \033[93;1mUnRAR files ...\033[0m', unit='%', position=0, leave=True, colour="blue") as pbar:
                current_file = None
                for output_line in process.stdout:
                    match = self.progress_regex.search(output_line)
                    file_match = self.file_info_regex.search(output_line)

                    if match:
                        percent = int(match.group(1))
                        pbar.update(percent - pbar.n)
                    elif file_match:
                        current_file = os.path.basename(file_match.group(1))
                        pbar.set_description(f' \033[93;1mUnRAR\033[0m \033[91;1m{current_file}\033[0m')

                if 'All OK' in output_line:
                    pbar.update(100 - pbar.n)

            process.wait()

            if 'All OK' not in output_line:
                print(f" \033[91;1mUnRAR error: ALL OK message NOT found!\033[0m")
                return False
            else:
                if __printdebug__: print(f" \033[93;1mUnRAR ALL OK ... remvoing RAR files ...\033[0m")
                self.delete_rar_files(allRARFiles)
                return True
        except Exception as e:
            print(f" \033[91;1mUnRAR error: {e}\033[0m")
            return False

def bytes2human(byte_size, base=1024):
    if byte_size == 0:
        return "0 B"
    size_names = ["B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB"]
    exponent = min(int(log2(byte_size) // log2(base)), len(size_names) - 1)
    converted_size = round(byte_size / (base ** (exponent)), 2)
    return f"{converted_size} {size_names[exponent]}"

def readSFDL(sfdl_file, password):
    sfdl_data = {}
    
    root = ET.fromstring(sfdl_file)

    encrypted = root.find('Encrypted').text
    release_name = root.find('Description').text
    
    connection_info = root.find('ConnectionInfo')
    
    if connection_info is not None:
        ftp_host = connection_info.find('Host').text if connection_info.find('Host') is not None else None
        ftp_port = connection_info.find('Port').text if connection_info.find('Port') is not None else None
        ftp_user = connection_info.find('Username').text if connection_info.find('Username') is not None else None
        ftp_pass = connection_info.find('Password').text if connection_info.find('Password') is not None else None
        ftp_path = connection_info.find('BulkFolderPath').text if connection_info.find('BulkFolderPath') is not None else None

    ftp_path = root.find('Packages/SFDLPackage/BulkFolderList/BulkFolder/BulkFolderPath').text if root.find('Packages/SFDLPackage/BulkFolderList/BulkFolder/BulkFolderPath') is not None else None
    
    if encrypted == 'true':
        release_name = decrypt_aes_cbc_128(release_name, password)
        ftp_host = decrypt_aes_cbc_128(ftp_host, password)
        ftp_user = decrypt_aes_cbc_128(ftp_user, password)
        ftp_pass = decrypt_aes_cbc_128(ftp_pass, password)
        ftp_path = decrypt_aes_cbc_128(ftp_path, password)
        
    sfdl_data['release_name'] = release_name
    sfdl_data['ftp_host'] = ftp_host
    sfdl_data['ftp_port'] = ftp_port
    sfdl_data['ftp_user'] = ftp_user
    sfdl_data['ftp_pass'] = ftp_pass
    sfdl_data['ftp_path'] = ftp_path
    
    if sfdl_data:
        return sfdl_data
    else:
        return None

# get SFDL file from url or local file
# url can be a local file or web source http(s)
def getSFDL(url, form_data=None):
    filename = url.split("/")[-1]
    print(f" \033[93;1mOpen SFDL file:\033[0m \033[94;1m{filename}\033[0m")
    
    url_pattern = re.compile(r'https?://\S+')
    if re.match(url_pattern, url):
        try:
            form_data = {'download': 'true'}
            response = requests.post(url, data=form_data)
            response.raise_for_status()
            filename = None
            content_disposition = response.headers.get('Content-Disposition')
            if content_disposition:
                match = re.search(r'filename=["\'](.*?)["\']', content_disposition)
                if match:
                    filename = match.group(1)
            if not filename:
                filename = 'temp.sfdl'
                
            temp_folder = tempfile.gettempdir()
            temp_file_path = os.path.join(temp_folder, filename)

            with open(temp_file_path, 'wb') as file:
                file.write(response.content)

            with open(temp_file_path, 'r') as file:
                content = file.read()
                return content
        except requests.exceptions.RequestException as e:
            print(f" \033[91;1mError downloading SFDL file: {e}\033[0m")
    else:
        if os.path.exists(url):
            with open(url, 'rb') as file:
                content = file.read()
                return content
        else:
            print("SFDL Error: Enter URL or local file only!")
            print("URL Example: https://download.schnuffy.net/enc/00000000;MyRelease.action.movie.3033-SAUGER")
            print("Local file: /home/user/downloads/MyRelease.action.movie.3033-SAUGER.sfdl or")
            print("Local file: C:/User/Downloads/MyRelease.action.movie.3033-SAUGER.sfdl")

# decrypt sfdl
def decrypt_aes_cbc_128(encoded_message, password):
    decoded_message = base64.b64decode(encoded_message)
    iv = decoded_message[:16]
    key = hashlib.md5(password.encode('latin-1')).digest()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    decrypted_message = decryptor.update(decoded_message[16:]) + decryptor.finalize()
    padding_length = decrypted_message[-1]
    result = decrypted_message[:-padding_length]
    return result.decode('latin-1')

# connect to ftp server and create a file index
def get_ftp_file_index(ftp_host, ftp_port, ftp_user, ftp_pass, ftp_path, proxy, release_name):
    print(f" \033[93;1mGet FTP-Index for:\033[0m \033[95;1m{release_name}\033[0m")
    try:
        ftp_client = FTPList(ftp_host, ftp_port, ftp_user, ftp_pass, ftp_path, proxy)
        ftp_client.ftp_login()
        files = ftp_client.list_files()
        return files
    except (error_temp, error_perm, error_proto, error_reply, Error, socket_error) as e:
        print(f" \033[91;1mFTP-List Error: {e}\033[0m")
    finally:
        if ftp_client:
            ftp_client.close()

# connect to ftp server and download files for index
def download_files(ftp_host, ftp_port, ftp_user, ftp_pass, destination, max_threads, release_name, files, proxy, sfdl_file):
    print(f" \033[93;1mStart Download:\033[0m \033[95;1m{release_name}\033[0m")
    total_size = bytes2human(sum(file_size for _, file_size in files), base=1000)
    print(f" \033[93;1mLoading\033[0m \033[92;1m{len(files)}\033[0m \033[93;1mfiles\033[0m \033[92;1m({total_size})\033[0m \033[93;1musing\033[0m \033[92;1m{max_threads}\033[0m \033[93;1mthreads\033[0m")
    try:
        ftp_downloader = FTPDownloader(ftp_host, ftp_port, ftp_user, ftp_pass, destination, max_threads, release_name, proxy, sfdl_file)
        ftp_downloader.connect()
        ftp_downloader.download_multiple_files(files)
    except (error_temp, error_perm, error_proto, error_reply, Error, socket_error) as e:
        print(f" \033[91;1mFTP-Download Error: {e}\033[0m")

# help the user to install missing packages using pip
def check_and_install_packages(packages):
    missing_packages = []

    # check for missing required python packages
    for package in packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print("Missing Python packages: {}".format(", ".join(missing_packages)))
        
        def check_pip_availability():
            return shutil.which('pip') is not None
        
        # check for pip
        if not check_pip_availability():
            print("pip is not available! Can't help you install missing Python packages ...")
            print("... you are on your own, good luck!")
            return False
    
        # runnung pip
        print("Running: pip install {}".format(" ".join(missing_packages)))
        install_command = ["pip", "install"] + missing_packages

        try:
            subprocess.check_call(install_command)
            print("Success! All missing Python packages are now installed!")
            return True
        except subprocess.CalledProcessError as e:
            print("Error: pip was not able to install all the packages!") 
            return False

    return True  # Keine fehlenden Pakete

def main(ftp_host, ftp_port, ftp_user, ftp_pass, ftp_path, destination, max_threads, release_name, proxy, sfdl_file): 
    files = None
    files = get_ftp_file_index(ftp_host, ftp_port, ftp_user, ftp_pass, ftp_path, proxy, release_name)
    
    if files is not None and len(files) > 0:
        download_files(ftp_host, ftp_port, ftp_user, ftp_pass, destination, max_threads, release_name, files, proxy, sfdl_file)
    else:
        print(" \033[91;1mError: No files to download! (Empty files index)\033[0m")

def printBanner():
    os.system('cls' if os.name == 'nt' else 'clear') # clear console
    banner = r'''
                  _____ ______ _____  _       _____                             
                 / ____|  ____|  __ \| |     / ____|                            
     _ __  _   _| (___ | |__  | |  | | |    | (___   __ _ _   _  __ _  ___ _ __ 
    | '_ \| | | |\___ \|  __| | |  | | |     \___ \ / _` | | | |/ _` |/ _ \ '__|
    | |_) | |_| |____) | |    | |__| | |____ ____) | (_| | |_| | (_| |  __/ |   
    | .__/ \__, |_____/|_|    |_____/|______|_____/ \__,_|\__,_|\__, |\___|_|   
    | |     __/ |                                                __/ |          
    |_|    |___/                                                |___/           

    '''
    
    colored_lines = f"\033[92m{banner}\033[0m"
    print(colored_lines)
    print(f" \033[93;1mpySFDLSauger \033[91;1m{__version__}\033[0m \033[93;1m(GrafSauger)\033[0m")

# pySFDLSauger (GrafSauger)
# Nur die harten Sauger kommen durch!
if __name__ == "__main__":
    printBanner()
    
    parser = argparse.ArgumentParser(description=f'''pySFDLSauger {__version__} (GrafSauger)
    Example: pySFDLSauger.py --sfdl /home/user/downloads/my.sfdl
    Example: pySFDLSauger.py --sfdl https://download.schnuffy.net/enc/00000000;MyRelease.action.movie.3033-SAUGER
    Example: pySFDLSauger.py --sfdl C:/downloads/my.sfdl --destination C:/downloads --threads 10''', formatter_class=argparse.RawDescriptionHelpFormatter)
    
    parser.add_argument("-i", "--sfdl", help="SFDL File")
    parser.add_argument("-d", "--destination", help="Download destination")
    parser.add_argument("-t", "--threads", help="Max download threads (default: 3)")
    parser.add_argument("-p", "--password", help="SFDL Password (default: mlcboard.com)")
    parser.add_argument("-m", "--monitor", help="Monitor path for SFDL files [auto downloader] (default: None)")
    parser.add_argument("-u", "--unrar", help="Use UnRAR to extract downloads (default: True)")
    parser.add_argument("--proxy_host", help="Socks5 Host")
    parser.add_argument("--proxy_port", help="Socks5 Port")
    parser.add_argument("--proxy_user", help="Socks5 Username")
    parser.add_argument("--proxy_pass", help="Socks5 Password")
    parser.add_argument("--debug", help="Debug (default: None)")
    parser.add_argument("--nockeck", help="Disable package check (default: None)")
    
    args = parser.parse_args()
    
    # check for missing python packages and try to install them using pip
    nockeck = args.nockeck if args.nockeck is not None else None
    if nockeck is None:
        if not check_and_install_packages(__required_packages__):
            print("There are still missing Python packages to run pySFDLSauger!")
            print("Please install all missing packages first and try again!")
            print("END OF LINE")
            sys.exit(1)

    sfdl = args.sfdl if args.sfdl is not None else None
    destination = args.destination if args.destination is not None else None
    threads = args.threads if args.threads is not None else 3
    password = args.password if args.password is not None else None
    monitor = args.monitor if args.monitor is not None else None
    
    __use_unrar__ = None if args.unrar is not None else True
    
    proxy_host = args.proxy_host if args.proxy_host is not None else None
    proxy_port = args.proxy_port if args.proxy_port is not None else None
    proxy_user = args.proxy_user if args.proxy_user is not None else None
    proxy_pass = args.proxy_pass if args.proxy_pass is not None else None
    
    debug = args.debug if args.debug is not None else None
    if debug is not None:
        __printdebug__ = True
    
    if destination is None:
        if os.name == 'posix':
            destination = str(os.path.join(Path.home(), "Downloads"))
        elif os.name == 'nt':
            destination = str(os.path.join(Path.home(), "Downloads"))
        else:
            destination = os.getcwd()

    # set socks5 proxy
    proxy = None
    if proxy_host is not None and proxy_port is not None:
        proxy = Proxy(proxy_host, proxy_port, username=proxy_user, password=proxy_pass)
    
    # set default password for encrypted sfdl files
    if password is None:
        password = "mlcboard.com"
    
    # start watchdog service to monitor path for new sfdl files
    if monitor is not None:
        __monitor_mode__ = True
        watchdog_path = os.path.normpath(monitor)
        if os.path.exists(watchdog_path) and os.path.isdir(watchdog_path):
            watcher = FileWatcher(watchdog_path, password, destination, threads)
            watcher.start_watching()
        else:
            print(f" \033[91;1mError: Sorry, but {watchdog_path} does not exist!\033[0m")
            parser.print_help()
            sys.exit(1)
    
    if sfdl is None:
        print(" \033[91;1mError: No SFDL file set!\033[0m")
        parser.print_help()
        sys.exit(1)
    
    # get SFDL file data from web or local file
    sfdl_file = getSFDL(sfdl)
    
    sfdl_data = readSFDL(sfdl_file, password)
    release_name, ftp_host, ftp_port, ftp_user, ftp_pass, ftp_path = (None, None, None, None, None, None)
    if sfdl_data is not None:
        release_name = sfdl_data['release_name']
        ftp_host = sfdl_data['ftp_host']
        ftp_port = sfdl_data['ftp_port']
        ftp_user = sfdl_data['ftp_user']
        ftp_pass = sfdl_data['ftp_pass']
        ftp_path = sfdl_data['ftp_path']

    if __printdebug__:
        print("===== DEBUG ====")
        print(f"SFDL: {sfdl}")
        print(f"SFDL-Pass: {password}")
        print(f"Release-Name: {release_name}")
        print(f"FTP-Host: {ftp_host}")
        print(f"FTP-Port: {ftp_port}")
        print(f"FTP-User: {ftp_user}")
        print(f"FTP-Pass: {ftp_pass}")
        print(f"Threads: {threads}")
        print(f"Destination: {destination}")
        print(f"proxy_host: {proxy_host}")
        print(f"proxy_port: {proxy_port}")
        print(f"proxy_user: {proxy_user}")
        print(f"proxy_pass: {proxy_pass}")
        print("===== DEBUG ====")

    if all(variable is not None for variable in [ftp_host, ftp_port, ftp_path]):
        main(ftp_host, int(ftp_port), ftp_user, ftp_pass, ftp_path, destination, int(threads), release_name, proxy, sfdl)
    else:
        print(f" \033[91;1mError: Missing FTP data from SFDL file!\033[0m")
        parser.print_help()
        sys.exit(1)