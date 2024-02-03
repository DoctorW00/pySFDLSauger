import sys, os, argparse, threading, time, socks, re, requests, tempfile, base64, hashlib, tqdm
from pathlib import Path
from socket import error as socket_error
from ftplib import FTP, error_temp, error_perm, error_proto, error_reply, Error
from urllib.parse import unquote
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from math import log2
import xml.etree.ElementTree as ET

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
                # print(f"FTPList: FTP Connection Closed!")
            except AttributeError:
                pass
            finally:
                self.ftp = None

class FTPDownloader:
    def __init__(self, ftp_host, ftp_port=21, ftp_user="anonymous", ftp_pass="anonymous@sauger.local", download_folder=None, max_threads=10, release_name=None, proxy=None):
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
        self.bar = None # main progress for the whole download
        self.bars = []  # progressbars for files
        self.bars_count = 0

    def ensure_directory_exists(self, file_path):
        directory = os.path.dirname(file_path)
        if not os.path.exists(directory):
            os.makedirs(directory)

    def get_release_from_path(self, path):
        release = None
        last_slash_index = path.rfind('/')
        if last_slash_index != -1:
            path = path[:last_slash_index]
            new_last_slash_index = path.rfind('/')
            if new_last_slash_index != -1:
                release = path[new_last_slash_index + 1:]
        return release
    
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
            print(f" \033[91;1m[1] FTP Connection Error in get_ftp_session: {e}\033[0m")
            return None
        except EOFError as eof_error:
            print(f" \033[91;1m[1] EOFError in get_ftp_session: {eof_error}\033[0m")
            return None
    
    def download_multiple_files(self, file_list):
        total_size = sum(file_size for _, file_size in file_list)
        total_files = len(file_list)
        
        self.bar = tqdm.tqdm(total=total_size, unit_scale=True, desc=f' \033[91;1m{self.release_name}\033[0m', miniters=1, file=sys.stdout, leave=True, colour="green")

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

    def download_in_thread(self, remote_path, local_file, file_size, total_files):
        newBarIndex = len(self.bars)
        ftp = None
        e = None
        try:
            try:
                # ftp = self.connect()
                ftp = self.get_ftp_session()
            except (error_temp, error_perm, error_proto, error_reply, Error, socket_error) as e:
                print(f" \033[91;1mDownload Thread Error: {e}\033[0m")
            
            if ftp is not None:
                with self.thread_semaphore:
                    self.download_with_progress(ftp, remote_path, local_file, file_size, total_files, newBarIndex)
            else:
                print(f" \033[91;1m[1] FTP Connection Error: {e}\033[0m")
        except threading.ThreadError as te:
            print(f" \033[91;1mDownload Thread Error: {te}\033[0m")
        finally:
            if ftp is not None:
                # print("[0] Downloaded " + str(local_file) + " successfully!")
                ftp.close()
            if newBarIndex < len(self.bars):
                self.bars[newBarIndex].close()
                self.bars[newBarIndex].clear()
            else:
                self.bars[0].close()
                self.bars[0].clear()

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
                self.bars_count += 1
                
                ftp.retrbinary(f"RETR {remote_path}", lambda data: self.write_with_progress(data, local_filepath, remote_path, file_size, total_files, newBarIndex), blocksize=1024)
                
            except (error_temp, error_perm, error_proto, error_reply, Error, socket_error) as e:
                # retry if server responds max connections reached
                error_message = str(e).lower().strip()
                if error_message.startswith("553") or error_message.startswith("530"):
                    if ftp is not None:
                        # print("[2] Download: Closing connection!")
                        ftp.close()
                    # print("[2] Download: Server maximum connections reached ... retry in 10 ...")
                    time.sleep(10)
                    self.download_in_thread(remote_path, local_file, file_size, total_files)
                    sys.exit() # end current thread
                else:
                    print(f" \033[91;1m[2] FTP Connection Error: {e}\033[0m")
            finally:
                if ftp is not None:
                    ftp.close()
                self.bars[newBarIndex].close()
                self.bars[newBarIndex].clear()

    def write_with_progress(self, data, local_filepath, remote_path, file_size, total_files, newBarIndex):
        if self.download_folder is None:
            local_filepath = os.path.join(self.download_folder, local_file)
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
        
        local_filepath = local_filepath.replace("//", "/")
        self.ensure_directory_exists(local_filepath)
        
        try:
            with open(local_filepath, 'ab') as local_file:
                local_file.write(data)
                if newBarIndex < len(self.bars):
                    self.bars[newBarIndex].update(len(data))
                    self.bar.update(len(data))
        except Exception as e:
            print(f" \033[91;1mError can't write file: {e}\033[0m")

    def ensure_directory_exists(self, file_path):
        directory = os.path.dirname(file_path)
        if not os.path.exists(directory):
            os.makedirs(directory)

def bytes2human(byte_size, base=1024):
    if byte_size == 0:
        return "0 B"
    size_names = ["B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB"]
    exponent = min(int(log2(byte_size) // log2(base)), len(size_names) - 1)
    converted_size = round(byte_size / (base ** (exponent)), 2)
    return f"{converted_size} {size_names[exponent]}"

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

# connect to ftp server and download files from index
def download_files(ftp_host, ftp_port, ftp_user, ftp_pass, destination, max_threads, release_name, files, proxy):
    print(f" \033[93;1mStart Download:\033[0m \033[95;1m{release_name}\033[0m")
    total_size = bytes2human(sum(file_size for _, file_size in files), base=1000)
    print(f" \033[93;1mLoading\033[0m \033[92;1m{len(files)}\033[0m \033[93;1mfiles\033[0m \033[92;1m({total_size})\033[0m \033[93;1musing\033[0m \033[92;1m{max_threads}\033[0m \033[93;1mthreads\033[0m")
    try:
        ftp_downloader = FTPDownloader(ftp_host, ftp_port, ftp_user, ftp_pass, destination, max_threads, release_name, proxy)
        ftp_downloader.connect()
        ftp_downloader.download_multiple_files(files)
    except (error_temp, error_perm, error_proto, error_reply, Error, socket_error) as e:
        print(f" \033[91;1mFTP-Download Error: {e}\033[0m")

def main(ftp_host, ftp_port, ftp_user, ftp_pass, ftp_path, destination, max_threads, release_name, proxy): 
    files = None
    files = get_ftp_file_index(ftp_host, ftp_port, ftp_user, ftp_pass, ftp_path, proxy, release_name)
    
    if files is not None and len(files) > 0:
        download_files(ftp_host, ftp_port, ftp_user, ftp_pass, destination, max_threads, release_name, files, proxy)
    else:
        print(" \033[91;1mError: No files to download! (Empty files index)\033[0m")

def printBanner():
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


# pySFDLSauger (GrafSauger)
# Nur die harten Sauger kommen durch!
if __name__ == "__main__":
    VERSION = '2.0.1'
    
    os.system('cls' if os.name == 'nt' else 'clear') # clear console
    printBanner()
    print(f" \033[93;1mpySFDLSauger \033[91;1m{VERSION}\033[0m \033[93;1m(GrafSauger)\033[0m")
    
    parser = argparse.ArgumentParser(description='''pySFDLSauger {VERSION} (GrafSauger)
    Example: pySFDLSauger.py --sfdl /home/user/downloads/my.sfdl
    Example: pySFDLSauger.py --sfdl https://download.schnuffy.net/enc/00000000;MyRelease.action.movie.3033-SAUGER
    Example: pySFDLSauger.py --sfdl C:/downloads/my.sfdl --destination C:/downloads --threads 10''', formatter_class=argparse.RawDescriptionHelpFormatter)
    
    parser.add_argument("-i", "--sfdl", help="SFDL File")
    parser.add_argument("-d", "--destination", help="Download destination")
    parser.add_argument("-t", "--threads", help="Max download threads (default: 3)")
    parser.add_argument("-p", "--password", help="SFDL Password (default: mlcboard.com)")
    parser.add_argument("--proxy_host", help="Socks5 Host")
    parser.add_argument("--proxy_port", help="Socks5 Port")
    parser.add_argument("--proxy_user", help="Socks5 Username")
    parser.add_argument("--proxy_pass", help="Socks5 Password")
    parser.add_argument("--debug", help="Debug (default: None)")
    
    args = parser.parse_args()

    sfdl = args.sfdl if args.sfdl is not None else None
    destination = args.destination if args.destination is not None else None
    threads = args.threads if args.threads is not None else 3
    password = args.password if args.password is not None else None
    
    proxy_host = args.proxy_host if args.proxy_host is not None else None
    proxy_port = args.proxy_port if args.proxy_port is not None else None
    proxy_user = args.proxy_user if args.proxy_user is not None else None
    proxy_pass = args.proxy_pass if args.proxy_pass is not None else None
    
    debug = args.debug if args.debug is not None else None
    
    if sfdl is None:
        print(" \033[91;1mError: No SFDL file set!\033[0m")
        parser.print_help()
        sys.exit(1)
    
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

    # get SFDL file data from web or local file
    sfdl_file = getSFDL(sfdl)
    
    # set default password for encrypted sfdl files
    if password is None:
        password = "mlcboard.com"

    # XML-Datei einlesen
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

    if debug is not None:
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

    main(ftp_host, int(ftp_port), ftp_user, ftp_pass, ftp_path, destination, int(threads), release_name, proxy)