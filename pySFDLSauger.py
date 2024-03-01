import sys, os, argparse, threading, time, socks, re, requests, tempfile, base64, hashlib, tqdm, subprocess, shutil, platform
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
from concurrent.futures import ThreadPoolExecutor

__version__ = "2.1.6"
__printdebug__ = False
__download_running__ = False
__monitor_mode__ = False
__use_unrar__ = None
__exclude_files__ = []
__update_url__ = "https://raw.githubusercontent.com/DoctorW00/pySFDLSauger/main/pySFDLSauger.py"

class Proxy:
    def __init__(self, host, port, username=None, password=None):
        self.proxy = socks.socksocket()
        self.proxy.set_proxy(socks.SOCKS5, host, port, username=username, password=password)

    def connect(self, target_host, target_port):
        self.proxy.connect((target_host, target_port))

    def close(self):
        self.proxy.close()

class FTPList:
    def __init__(self, ftp_host=None, ftp_port=21, ftp_user="anonymous", ftp_pass="anonymous@sauger.local", ftp_path=None, release_name=None, proxy=None):
        self.ftp = None
        self.files = []
        self.files_index = 0
        self.ftp_host = ftp_host
        self.ftp_port = ftp_port
        self.ftp_user = ftp_user
        self.ftp_pass = ftp_pass
        self.ftp_path = ftp_path
        self.release_name = release_name
        self.exclude_files = __exclude_files__
        self.proxy = proxy
        self.saugerDesign = "\033[93;1m{desc}\033[0m"
        self.dummy_progressbar = tqdm.tqdm(total=None, desc=f' \033[93;1mFile index running ...\033[0m', bar_format=self.saugerDesign, miniters=1, file=sys.stdout, leave=False, colour="magenta")

    def file_by_index(self, index):
        if 0 <= index < len(self.files):
            return self.files[index]
        else:
            return None

    def ftp_login(self):
        __download_running__ = True
        try:
            if __printdebug__: print(f" \033[91;1mFTPList: Connect to ftp server ...\033[0m")
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

    def return_clean_ftp_path(self, path, item):
        clean_ftp_path = self.ftp_path.rstrip("/")
        rec_path = path.lstrip("./")
        clean_item = item.lstrip("./")
        final_full_file_path = None
        if rec_path == ".":
            final_full_file_path = clean_ftp_path + "/" + clean_item
        else:
            final_full_file_path = clean_ftp_path + "/" + rec_path + "/" + clean_item
        final_full_file_path = os.path.normpath(final_full_file_path).replace(os.sep, '/')
        return final_full_file_path

    def list_files(self, path="."):
        if self.ftp is None:
            self.ftp_login()
            pass

        full_path = f"{self.ftp_path}/{path}" if path != "." else self.ftp_path
        full_path = os.path.normpath(full_path).replace(os.sep, '/')

        try:
            if __printdebug__: print(f" \033[91;1mFTP get index for: {full_path}\033[0m")
            self.ftp.cwd(full_path)
        except Exception as e:
            if __printdebug__: print(f" \033[91;1mError: FTP index (cwd): {e}\033[0m")
            return
        
        files = {}
        
        # get some workaround going to get better results from more ftp servers
        # try mlsd command
        try:
            files_info_generator = self.ftp.mlsd(facts=["type", "size"])
            files_info = list(files_info_generator)
            if isinstance(files_info, list) and files_info:
                files = sorted(files_info, key=lambda x: x[0])
        except Exception as e:
            if __printdebug__: print(f" \033[91;1mFTP Error: {e}\033[0m")
            try:
                # try nlst + size command
                file_list_generator = self.ftp.nlst()
                file_list = list(file_list_generator)
                
                if isinstance(file_list, list) and file_list:
                    self.ftp.sendcmd("TYPE I")
                    files = {}
                    for item in file_list:
                        _, file_extension = os.path.splitext(item)
                        if file_extension:
                            try:
                                size = self.ftp.size(item)
                                files[item] = {'type': 'file', 'size': size}
                            except Exception as e:
                                files[item] = {'type': 'file', 'size': None}
                    
                    files = sorted(files.items(), key=lambda x: x[0])
            except Exception as e:
                if __printdebug__: print(f" \033[91;1mFTP Error: {e}\033[0m")
                pass

        try:
            for item, data in files:
                if data["type"] == "file":
                    self.dummy_progressbar.set_description(f' \033[93;1mFile:\033[0m \033[92;1m{item}\033[0m')
                    size = int(data["size"])
                    final_full_file_path = self.return_clean_ftp_path(path, item)
                    # check for files to exclude from download
                    match = any(element in item.lower() for element in self.exclude_files)
                    if match:
                        # exlude from download
                        if __printdebug__: print(f" \033[91;1mFTP-Index exclude file: {final_full_file_path}\033[0m")
                    else:
                        self.files.append((final_full_file_path, size))
                        if __printdebug__: print(f" \033[91;1mFTP-Index file found: {final_full_file_path}\033[0m")
                # also index all sub-dirs
                elif data["type"] == "dir":
                    self.dummy_progressbar.set_description(f' \033[93;1mSub-Dir:\033[0m \033[92;1m{item}\033[0m')
                    subdirectory_path = os.path.normpath(item).replace(os.sep, '/')
                    if __printdebug__: print(f" \033[91;1mFTP-Index found sub-dir: {subdirectory_path}\033[0m")
                    try:
                        self.list_files(subdirectory_path)
                    except Exception as e:
                        if __printdebug__: print(f" \033[91;1mError: FTP list subdir: {subdirectory_path} {e}\033[0m")
                        pass
        except Exception as e:
            if __printdebug__: print(f" \033[91;1mFTP Error: {e}\033[0m")
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
                if __printdebug__: print(f" \033[91;1mFTPList: FTP Connection Closed!\033[0m")
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
        self.bars_count = 0
        self.start_time = 0
        self.done_time = 0
        self.b2h = bytes2human
        self.local_download_path = None
        self.executor = None

    def write_speedreport(self, path, line1, line2):
        speedreport = path + '/speedreport.txt'
        try:
            with open(speedreport, 'w') as file:
                file.write(f'Speedreport: [B]{line1}[/B]\n')
                file.write('[HR][/HR]\n')
                file.write(f'{line2}\n')
                file.write(f'Thanks! :lv6:\n')
                file.write(f'\n')
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
                # 553 & 530 server full or max ip; 421 transfer timeout
                if error_message.startswith("553") or error_message.startswith("530") or error_message.startswith("421"):
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
    
    def stop_all_threads(self):
        if self.executor is not None:
            self.executor.shutdown(wait=True)
    
    def download_multiple_files(self, file_list):
        __download_running__ = True
        self.start_time = time.time()
        
        total_size = sum(file_size for _, file_size in file_list)
        total_files = len(file_list)
        
        saugerDesign = "\033[93;1m{desc}\033[0m \033[93;1m{percentage:3.0f}%\033[0m \033[93;1m|\033[0m{bar}\033[93;1m|\033[0m \033[93;1m{n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}{postfix}]\033[0m"
        self.bar = tqdm.tqdm(total=total_size, unit_scale=True, dynamic_ncols=True, bar_format=saugerDesign, desc=f' \033[91;1m{self.release_name}\033[0m', miniters=1, file=sys.stdout, leave=True, colour="green")

        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            self.executor = executor
            futures = []
            for remote_path, file_size in file_list:
                local_file = os.path.basename(remote_path)
                future = executor.submit(self.download_in_thread, remote_path, local_file, file_size, total_files)
                futures.append(future)

            for future in futures:
                future.result()
            
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
        
        __download_running__ = False
        
        # start next download if there is one
        if __monitor_mode__ is True:
            time.sleep(5)
            nextDownload = WatcherHandler
            nextDownload.update_file_paths

    def download_in_thread(self, remote_path, local_file, file_size, total_files):
        ftp = None
        e = None
        newBarIndex = self.bars_count
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
                ftp.close()
            # remove file progressbar
            if newBarIndex < len(self.bars):
                self.bars[newBarIndex].clear()
                self.bars[newBarIndex].close()
            else:
                self.bars[0].clear()
                self.bars[0].close()
            if __printdebug__: print(f" \033[93;1mDownloaded\033[0m \033[92;1m{local_file}\033[0m \033[93;1msuccessfully!\033[0m")

    def download_with_progress(self, ftp, remote_path, local_file, file_size, total_files, newBarIndex):
        local_filepath = os.path.join(self.download_folder, local_file)
        if ftp is None:
            ftp = self.connect()
        
        if ftp is not None:
            try:
                local_filename = os.path.basename(local_filepath)   
                restarg = {}
                
                saugerDesign = "\033[93;1m{desc}\033[0m \033[93;1m{percentage:3.0f}%\033[0m \033[93;1m|\033[0m{bar}\033[93;1m|\033[0m \033[93;1m{n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}{postfix}]\033[0m"
                if newBarIndex < len(self.bars):
                    self.bars[newBarIndex] = tqdm.tqdm(total=file_size, unit_scale=True, bar_format=saugerDesign, desc=f' \033[93;1mLoading\033[0m \033[92;1m{local_filename}\033[0m', miniters=1, file=sys.stdout, leave=False, colour="yellow")
                else:
                    self.bars.append(tqdm.tqdm(total=file_size, unit_scale=True, bar_format=saugerDesign, desc=f' \033[93;1mLoading\033[0m \033[92;1m{local_filename}\033[0m', miniters=1, file=sys.stdout, leave=False, colour="yellow"))
                
                # check if we got a partial file and continue download if so
                filePath = os.path.normpath(self.return_local_file_path(local_filepath, remote_path))
                if os.path.exists(filePath):
                    local_file_size = os.path.getsize(filePath)
                    if local_file_size >= file_size:
                        if __printdebug__: print(f" Download: Skipping {local_filepath} is already downloaded!")
                        # update progress
                        if newBarIndex < len(self.bars):
                            self.bars[newBarIndex].update(file_size)
                        else:
                            self.bars[0].update(file_size)
                        self.bar.update(file_size)
                        return
                    restarg = {'rest': str(local_file_size)} # resume at local file size
                
                # start downloading the file
                ftp.retrbinary(f"RETR {remote_path}", lambda data: self.write_with_progress(data, local_filepath, remote_path, file_size, total_files, newBarIndex), blocksize=1024, **restarg)
                
            except (error_temp, error_perm, error_proto, error_reply, Error, socket_error) as e:
                # retry if server responds max connections reached
                error_message = str(e).lower().strip()
                # 553 & 530 server full or max ip; 421 transfer timeout
                if error_message.startswith("553") or error_message.startswith("530") or error_message.startswith("421"):
                    if ftp is not None:
                        if __printdebug__: print("[2] Download: Closing connection!")
                        ftp.close()
                    if __printdebug__: print("[2] Download: Server maximum connections reached ... retry in 10 ...")
                    time.sleep(10)
                    self.download_in_thread(remote_path, local_file, file_size, total_files)
                    return
                else:
                    print(f" \033[91;1m[2] FTP Connection Error: {e}\033[0m")
            finally:
                if ftp is not None:
                    ftp.close()

    def write_with_progress(self, data, local_filepath, remote_path, file_size, total_files, newBarIndex):
        local_filepath = self.return_local_file_path(local_filepath, remote_path)
        self.ensure_directory_exists(local_filepath)
        fileSize = 0 
        if os.path.exists(local_filepath):
            fileSize = os.path.getsize(local_filepath)
        try:
            with open(local_filepath, 'ab') as local_file:
                local_file.seek(0, 2)
                local_file.write(data)
                if newBarIndex < len(self.bars):
                    if fileSize < 0:
                        self.bars[newBarIndex].update(len(data) + fileSize)
                        self.bar.update(len(data) + fileSize)
                    else:
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
                        if __printdebug__: print(f" \033[91;1mSFDL found: {file_path}\033[0m")
                        self.file_paths.append(file_path)
                        self.update_file_paths()

    def on_created(self, event):
        if event.is_directory:
            return
        file_path = event.src_path
        if file_path.lower().endswith(".sfdl") and file_path not in self.file_paths and os.path.exists(file_path):
            if __printdebug__: print(f" \033[91;1mNew SFDL found: {file_path}\033[0m")
            self.file_paths.append(file_path)
            self.update_file_paths()

    def on_modified(self, event):
        if not event.is_directory:
            file_path = event.src_path
            if file_path.lower().endswith(".sfdl") and file_path not in self.file_paths and os.path.exists(file_path):
                if __printdebug__: print(f" \033[91;1mExisting SFDL found: {file_path}\033[0m")
                self.file_paths.append(file_path)
                self.update_file_paths()
                
    def on_deleted(self, event):
        if not event.is_directory:
            file_path = event.src_path
            if file_path.lower().endswith(".sfdl") and file_path in self.file_paths:
                if __printdebug__: print(f" \033[91;1mSFDL {file_path} got deleted!\033[0m")
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
                if __printdebug__: print(f" \033[91;1mSFDL {file_path} got deleted or is no longer accessible!\033[0m")
                
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
        self.saugerDesign = "\033[93;1m{desc}\033[0m \033[93;1m{percentage:3.0f}%\033[0m \033[93;1m|\033[0m{bar}\033[93;1m|\033[0m \033[93;1m{n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}{postfix}]\033[0m"

    def list_subdirectories(self, root_path):
        subdirectories = []
        subdirectories.append(root_path)
        def _list_subdirectories_recursive(current_path):
            nonlocal subdirectories
            for item in os.listdir(current_path):
                item_path = os.path.join(current_path, item)
                if os.path.isdir(item_path):
                    subdirectories.append(item_path)
                    _list_subdirectories_recursive(item_path)
        _list_subdirectories_recursive(root_path)
        return subdirectories

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
        for rar_file in tqdm.tqdm(rar_files, bar_format=self.saugerDesign, desc=" \033[93;1mRemoving RAR files ...\033[0m", unit="file", colour="magenta"):
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
        rar_errors = 0
        allsubfolders = self.list_subdirectories(self.rar_path)
        for folder in allsubfolders:
            
            print(f" \033[93;1mUnRAR enter dir:\033[0m \033[92m{folder}\033[0m")
            
            allRARFiles = self.find_all_rar_files(folder)
            firstRAR = self.find_rar_file(folder)
            
            if firstRAR is None:
                if __printdebug__: print(f" \033[91;1mUnRAR: No RAR file found in {folder}\033[0m")
                rar_errors += 1
                pass
            
            try:
                if not self.is_unrar_available():
                    raise Exception(f" \033[91;1mUnRAR error: Can\'t find UnRAR executable! Please install UnRAR first!\033[0m")

                command = ['unrar', 'x', '-o+', firstRAR, folder]
                if self.password:
                    command.extend(['-p' + self.password])

                process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
                
                with tqdm.tqdm(total=100, dynamic_ncols=True, bar_format=self.saugerDesign, desc=f' \033[93;1mUnRAR files ...\033[0m', unit='%', position=0, leave=True, colour="blue") as pbar:
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
                    rar_errors += 1
                    pass
                else:
                    if __printdebug__: print(f" \033[93;1mUnRAR ALL OK ... remvoing RAR files ...\033[0m")
                    self.delete_rar_files(allRARFiles)
                    pass
            except Exception as e:
                print(f" \033[91;1mUnRAR error: {e}\033[0m")
                rar_errors += 1
                pass
        
        if rar_errors:
            return False
        else:
            return True

class ScriptUpdater:
    def __init__(self, script_url, local_version=None):
        self.script_url = script_url
        self.local_version = local_version
        self.local_script_path = os.path.join(os.path.dirname(__file__), script_url.split("/")[-1])

    def check_for_update(self):
        try:
            response = requests.get(self.script_url, stream=True)
            response.raise_for_status()
            if response.status_code == 200:
                remote_version = re.search(r'__version__ = "([0-9.]+)"', response.text)
                if remote_version:
                    remote_version = remote_version.group(1)
                    if self.local_version is None or remote_version > self.local_version:
                        print(f" \033[93;1mThis version: \033[91;1m{self.local_version}\033[0m\033[93;1m, latest version\033[0m \033[92m{remote_version}.\033[0m")
                        update_choice = input(" \033[93;1mLoad update now? (y/n):\033[0m ").lower()
                        if update_choice in ['y', 'z', 'j']:
                            self._update_script(response)
                        else:
                            print(" \033[93;1mUpdate canceled.\033[0m")
                    else:
                        print(" \033[93;1mNo new version available. This version is up to date!\033[0m")
                else:
                    print(" \033[93;1mUnable to find version number.\033[0m")
            else:
                print(f" \033[91;1mUnable to access GitHub: {response.status_code}\033[0m")
        except requests.exceptions.RequestException as e:
            print(f" \033[91;1mUpdate request error: {e}\033[0m")
        except Exception as e:
            print(f" \033[91;1mUnknown update error: {e}\033[0m")

    def _update_script(self, response):
        try:
            with open(self.local_script_path, "wb") as local_file:
                for chunk in response.iter_content(chunk_size=128):
                    local_file.write(chunk)
            print(" \033[93;1mSuccessfully updated!\033[0m")
        except Exception as e:
            print(f" \033[91;1mUpdate error, unable to write file: {e}\033[0m")

def bytes2human(byte_size, base=1024):
    if byte_size == 0:
        return "0 B"
    size_names = ["B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB"]
    exponent = min(int(log2(byte_size) // log2(base)), len(size_names) - 1)
    converted_size = round(byte_size / (base ** (exponent)), 2)
    return f"{converted_size} {size_names[exponent]}"

def readSFDL(sfdl_file, password):
    sfdl_data = {}
    
    try:
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

        # ftp_paths = ftp_paths or [item.text for item in root.findall('Packages/SFDLPackage/BulkFolderList/BulkFolder/BulkFolderPath')]
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

    except Exception as e:
        print(f" \033[91;1m SFDL read error: {e}\033[0m")
        return None

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
            print(" \033[1;97mSFDL Error: Enter URL or local file only!\033[0m")
            print(" \033[1;97mURL Example: https://download.schnuffy.net/enc/00000000;MyRelease.action.movie.3033-SAUGER\033[0m")
            print(" \033[1;97mLocal file: /home/user/downloads/MyRelease.action.movie.3033-SAUGER.sfdl or\033[0m")
            print(" \033[1;97mLocal file: C:/User/Downloads/MyRelease.action.movie.3033-SAUGER.sfdl\033[0m")

# decrypt sfdl
def decrypt_aes_cbc_128(encoded_message, password):
    if not encoded_message:
        return None
    decoded_message = base64.b64decode(encoded_message)
    iv = decoded_message[:16]
    key = hashlib.md5(password.encode('latin-1')).digest()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    decrypted_message = decryptor.update(decoded_message[16:]) + decryptor.finalize()
    padding_length = decrypted_message[-1]
    result = decrypted_message[:-padding_length]
    return result.decode('latin-1')

def is_destination_valid(path):
    if os.access(path, os.W_OK):
        return True
    else:
        return False

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

def main(ftp_host, ftp_port, ftp_user, ftp_pass, ftp_path, destination, max_threads, release_name, proxy, sfdl_file): 
    files = None
    files = get_ftp_file_index(ftp_host, ftp_port, ftp_user, ftp_pass, ftp_path, proxy, release_name)
    
    if files is not None and len(files) > 0:
        disc_free_space_bytes = shutil.disk_usage(destination).free
        total_bytes = 0
        for file_info in files:
            total_bytes += file_info[1]
        
        if __printdebug__:
            print(f" \033[93;1mFiles:\033[0m")
            for file in files:
                print(f" \033[93;1mFile: {file}\033[0m")
        
        # check for write premission
        if os.access(destination, os.W_OK):
            # check for free space
            if disc_free_space_bytes <= total_bytes:
                print(f" \033[91;1mError: Download size {bytes2human(total_bytes, base=1000)}, free space {bytes2human(disc_free_space_bytes, base=1000)}\033[0m")
                print(f" \033[91;1mError: Not enough free space at {destination}!\033[0m")
            else:
                download_files(ftp_host, ftp_port, ftp_user, ftp_pass, destination, max_threads, release_name, files, proxy, sfdl_file)
        else:
            print(f" \033[91;1mError: Unable to create new downloads in {destination} (write protection)\033[0m")
    else:
        print(" \033[91;1mError: No files to download! (Empty files index)\033[0m")

def printBanner():
    os.system('cls' if os.name == 'nt' else 'clear') # clear console
    if platform.system() == 'Darwin': # for macos change consol background to black
        script = f'tell application "Terminal" to set background color of window 1 to "black"'
        subprocess.run(["osascript", "-e", script])
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
    Example: pySFDLSauger.py -i /home/user/downloads/my.sfdl
    Example: pySFDLSauger.py -i https://download.schnuffy.net/enc/00000000;MyRelease.action.movie.3033-SAUGER
    Example: pySFDLSauger.py --sfdl C:/downloads/my.sfdl --destination C:/downloads --threads 10
    Example: pySFDLSauger.py -i C:/test.sfdl -d C:/downloads -t 3 --exclude ".scr, .vbs, sample, proof, .sub, .idx"''', formatter_class=argparse.RawDescriptionHelpFormatter)
    
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
    parser.add_argument("--exclude", help="Exclude files from download (default: '.scr, .vbs')")
    parser.add_argument("--update", help="Check and load new pySFDLSauger.py from GitHub")
    parser.add_argument("--debug", help="Debug (default: None)")
    
    args = parser.parse_args()

    update = args.update if args.update is not None else None
    if update is not None:
        print(f" \033[93;1mChecking for updates ...\033[0m")
        updater = ScriptUpdater(__update_url__, __version__)
        updater.check_for_update()
        sys.exit(0)

    sfdl = args.sfdl if args.sfdl is not None else None
    destination = args.destination if args.destination is not None else None
    threads = args.threads if args.threads is not None else 3
    password = args.password if args.password is not None else None
    monitor = args.monitor if args.monitor is not None else None
    
    __use_unrar__ = None if args.unrar is not None else True
    
    # files to exlucde from download
    exclude_list = None if args.exclude is not None else '.scr, .vbs'
    __exclude_files__ = [name.strip().lower() for name in exclude_list.split(",")]
    
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
            print("\033[1;97m") # white bold text
            parser.print_help()
            print("\033[0m") # default text
            sys.exit(1)
    
    if sfdl is None:
        print(" \033[91;1mError: No SFDL file set!\033[0m")
        print("\033[1;97m") # white bold text
        parser.print_help()
        print("\033[0m") # default text
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

    if is_destination_valid(destination) == False:
        print(f" \033[91;1mError: Unable to access or write to {destination}\033[0m")
        print("\033[1;97m") # white bold text
        parser.print_help()
        print("\033[0m") # default text
        sys.exit(1)

    if all(variable is not None for variable in [ftp_host, ftp_port, ftp_path]):
        main(ftp_host, int(ftp_port), ftp_user, ftp_pass, ftp_path, destination, int(threads), release_name, proxy, sfdl)
    else:
        print(f" \033[91;1mError: Missing FTP data from SFDL file!\033[0m")
        print("\033[1;97m") # white bold text
        parser.print_help()
        print("\033[0m") # default text
        sys.exit(1)