import sys, os, argparse, threading, time, socks, re, requests, tempfile, base64, hashlib, progressbar
from pathlib import Path
from socket import error as socket_error
from ftplib import FTP, error_temp, error_perm, error_proto, error_reply, Error
from urllib.parse import unquote
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
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
    def __init__(self, ftp_host=None, ftp_port=21, ftp_user="anonymous", ftp_pass="anonymous@pysauger.local", ftp_path=None, proxy=None):
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
        
        print("ftp_full_path: " + str(ftp_full_path))
        
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

    def update_progress(self, ftp_link, current_size, total_size):
        if self.progress_callback:
            self.progress_callback(ftp_link, current_size, total_size)

    def ftp_login(self):
        try:
            self.ftp = FTP()
            if self.proxy is not None:
                self.ftp.sock = self.proxy
            self.ftp.connect(self.ftp_host, self.ftp_port)
            self.ftp.login(self.ftp_user, self.ftp_pass)
            self.ftp.set_pasv
            self.ftp.encoding = "utf-8"
        except (error_temp, error_perm, error_proto, error_reply, Error, socket_error) as e:
            print(f"FTP Connection Error: {e}")
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

        files = sorted(self.ftp.mlsd(facts=["type", "size"]))

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
                print(f"FTPList: FTP Connection Closed!")
            except AttributeError:
                pass
            finally:
                self.ftp = None
    
class FTPDownloader:
    def __init__(self, ftp_host, ftp_port=21, ftp_user="anonymous", ftp_pass="anonymous@pysauger.local", download_folder=None, max_threads=10, release_name=None, proxy=None):
        self.ftp_host = ftp_host
        self.ftp_port = ftp_port
        self.ftp_user = ftp_user
        self.ftp_pass = ftp_pass
        self.download_folder = download_folder
        self.max_threads = max_threads
        self.thread_semaphore = threading.Semaphore(self.max_threads)
        self.release_name = release_name
        self.proxy = proxy

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
        ftp = FTP()
        if self.proxy is not None:
            ftp.sock = self.proxy
        ftp.connect(self.ftp_host, self.ftp_port)
        ftp.login(self.ftp_user, self.ftp_pass)
        ftp.set_pasv
        ftp.encoding = "utf-8"
        return ftp
    
    def download_multiple_files(self, file_list):
        total_size = sum(file_size for _, file_size in file_list)
        total_files = len(file_list)
        widgets = ['Files Loaded: ', progressbar.SimpleProgress(), '/', str(total_files), ' (',
                   'Size: ', progressbar.FileTransferSpeed(), ') ',
                   progressbar.Percentage(), ' ',
                   progressbar.Bar(marker='#', left='[', right=']')]
        total_bar = progressbar.ProgressBar(widgets=widgets, maxval=total_size // 1024).start()

        threads = []
        for remote_path, file_size in file_list:
            local_file = os.path.basename(remote_path)
            thread = threading.Thread(target=self.download_in_thread, args=(remote_path, local_file, file_size, total_bar, total_files))
            threads.append(thread)
            thread.start()
            time.sleep(0.1)

        for thread in threads:
            thread.join()

        total_bar.finish()

    def download_in_thread(self, remote_path, local_file, file_size, total_bar, total_files):
        ftp = self.connect()
        try:
            with self.thread_semaphore:
                self.download_with_progress(ftp, remote_path, local_file, file_size, total_bar, total_files)
        finally:
            ftp.quit()
            ftp = None
            self.proxy.close()

    def download_with_progress(self, ftp, remote_path, local_file, file_size, total_bar, total_files):
        local_filepath = os.path.join(self.download_folder, local_file)
        ftp.retrbinary(f"RETR {remote_path}", 
                        lambda data: self.write_with_progress(data, local_filepath, remote_path, file_size, total_bar, total_files),
                        blocksize=1024)
        print(f'File {remote_path} downloaded to {local_filepath}')

    def write_with_progress(self, data, local_filepath, remote_path, file_size, total_bar, total_files):
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
        
        with open(local_filepath, 'ab') as local_file:
            local_file.write(data)
            total_bar.update(local_file.tell() // 1024)

    def ensure_directory_exists(self, file_path):
        directory = os.path.dirname(file_path)
        if not os.path.exists(directory):
            os.makedirs(directory)

    def connect(self):
        ftp = FTP()
        if self.proxy is not None:
            ftp.sock = self.proxy
        ftp.connect(self.ftp_host, self.ftp_port)
        ftp.login(self.ftp_user, self.ftp_pass)
        ftp.set_pasv
        ftp.encoding = "utf-8"
        return ftp

    def show_progress(self, block_num, block_size, total_size, filename, bar):
        downloaded = block_num * block_size
        progress_percentage = (downloaded / total_size) * 100
        bar.update(downloaded // 1024)
        if progress_percentage == 100:
            print(f'File {filename} downloaded: {progress_percentage:.2f}%')

# get SFDL file from url or local file
# url can be a local file or web source http(s)
def getSFDL(url, form_data=None):
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
            print(f"Error downloading SFDL file: {e}")
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
def get_ftp_file_index(ftp_host, ftp_port, ftp_user, ftp_pass, ftp_path, proxy):
    try:
        ftp_client = FTPList(ftp_host, ftp_port, ftp_user, ftp_pass, ftp_path, proxy)
        ftp_client.ftp_login()
        files = ftp_client.list_files()
        return files
    except (error_temp, error_perm, error_proto, error_reply, Error, socket_error) as e:
        print(f"FTP-List Error: {e}")
    finally:
        if ftp_client:
            ftp_client.close()

# connect to ftp server and download files from index
def download_files(ftp_host, ftp_port, ftp_user, ftp_pass, destination, max_threads, release_name, files, proxy):
    try:
        ftp_downloader = FTPDownloader(ftp_host, ftp_port, ftp_user, ftp_pass, destination, max_threads, release_name, proxy)
        ftp_downloader.connect()
        ftp_downloader.download_multiple_files(files)
    except (error_temp, error_perm, error_proto, error_reply, Error, socket_error) as e:
        print(f"FTP-Download Error: {e}")

def main(ftp_host, ftp_port, ftp_user, ftp_pass, ftp_path, destination, max_threads, release_name, proxy): 
    files = None
    files = get_ftp_file_index(ftp_host, ftp_port, ftp_user, ftp_pass, ftp_path, proxy)
    
    if len(files) > 0:
        print(f"FTP-Index: {len(files)} files ready to download ...")
        download_files(ftp_host, ftp_port, ftp_user, ftp_pass, destination, max_threads, release_name, files, proxy)
    else:
        print("Error: No files to download! (Empty files index)")
    
# pySFDLSauger (GrafSauger)
# Nur die harten Sauger kommen durch!
if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description='''pySFDLSauger 2.0 (GrafSauger)
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
    
    args = parser.parse_args()

    sfdl = args.sfdl if args.sfdl is not None else None
    destination = args.destination if args.destination is not None else None
    threads = args.threads if args.threads is not None else None
    password = args.password if args.password is not None else None
    
    proxy_host = args.proxy_host if args.proxy_host is not None else None
    proxy_port = args.proxy_port if args.proxy_port is not None else None
    proxy_user = args.proxy_user if args.proxy_user is not None else None
    proxy_pass = args.proxy_pass if args.proxy_pass is not None else None
    
    if sfdl is None:
        print("Error: No SFDL file set!")
        parser.print_help()
        sys.exit(1)
    
    if destination is None:
        if os.name == 'posix':
            destination = str(os.path.join(Path.home(), "Downloads"))
        elif os.name == 'nt':
            destination = str(os.path.join(Path.home(), "Downloads"))
        else:
            destination = os.getcwd()
    
    if threads is None:
        threads = 3

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

    main(ftp_host, int(ftp_port), ftp_user, ftp_pass, ftp_path, destination, threads, release_name, proxy)