import sys, os, argparse, threading, time, socks, re, requests, tempfile, base64, hashlib, tqdm, subprocess, shutil, platform, websockets, asyncio, json, logging
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
from io import BytesIO
from zipfile import ZipFile
from flask import Flask, render_template_string

__version__ = "2.2.1"
__printdebug__ = False
__download_running__ = False
__monitor_mode__ = False
__use_unrar__ = None
__exclude_files__ = []
__update_url__ = "https://raw.githubusercontent.com/DoctorW00/pySFDLSauger/main/pySFDLSauger.py"
__use_web_gui__ = False
__web_gui_updates__ = []
__web_gui_logs__ = []
__ftp_loader__ = None
__file_watcher__ = None
__file_watcher_thread__ = None
__ftp_aborted__ = False
__web_data__ = """
    UEsDBBQAAAAAACaYZ1j3MNJ8vjMAAL4zAAAKAAAAaW5kZXguaHRtbDwhRE9DVFlQRSBodG1sPg0KPGh0bWwgbGFuZz0iZW4iPg0KPGhlYWQ+DQogICAgPG1ldGEgY2hhcnNldD0iVVRGLTgiPg0KICAgIDxtZXRhIGh0dHAtZXF1aXY9IlgtVUEtQ29tcGF0aWJsZSIgY29udGVudD0iSUU9ZWRnZSI+DQogICAgPG1ldGEgbmFtZT0idmlld3BvcnQiIGNvbnRlbnQ9IndpZHRoPWRldmljZS13aWR0aCwgaW5pdGlhbC1zY2FsZT0xLjAiPg0KICAgIDx0aXRsZT5weVNGRExTYXVnZXIgKHt7IHZlcnNpb24gfX0pIFdlYi1HVUk8L3RpdGxlPg0KICAgIDxzdHlsZT4NCgkJYm9keSB7DQoJCQlmb250LXNpemU6IDE2cHg7DQoJCQkvKiBiYWNrZ3JvdW5kOiAjMmIyYjJiOyAqLw0KCQkJYmFja2dyb3VuZDogcmdiKDc4LDc4LDc4KTsNCgkJCWJhY2tncm91bmQ6IGxpbmVhci1ncmFkaWVudCg5MGRlZywgcmdiYSg3OCw3OCw3OCwxKSAwJSwgcmdiYSg1Niw1Niw1NiwxKSA1MCUsIHJnYmEoNzgsNzgsNzgsMSkgMTAwJSk7DQoJCQljb2xvcjogd2hpdGU7DQoJCQltYXJnaW46IDA7DQoJCQlwYWRkaW5nOiAwOw0KICAgICAgICAgICAgZGlzcGxheTogZmxleDsNCiAgICAgICAgICAgIGFsaWduLWl0ZW1zOiBjZW50ZXI7DQogICAgICAgICAgICBqdXN0aWZ5LWNvbnRlbnQ6IGNlbnRlcjsNCiAgICAgICAgICAgIG1pbi1oZWlnaHQ6IDEwMHZoOw0KCQl9DQoJDQoJCSNsb2FkZXIgew0KCQkJd2lkdGg6IDk5OXB4Ow0KICAgICAgICAgICAgYmFja2dyb3VuZC1jb2xvcjogIzI0MjQyNDsNCiAgICAgICAgICAgIGFsaWduLWl0ZW1zOiBjZW50ZXI7DQogICAgICAgICAgICBwYWRkaW5nOiAwOw0KCQkJbWFyZ2luOiAwOw0KCQkJLXdlYmtpdC1ib3gtc2hhZG93OiAwcHggMHB4IDI5cHggMTFweCByZ2JhKDAsMCwwLDAuNjIpOw0KCQkJLW1vei1ib3gtc2hhZG93OiAwcHggMHB4IDI5cHggMTFweCByZ2JhKDAsMCwwLDAuNjIpOw0KCQkJYm94LXNoYWRvdzogMHB4IDBweCAyOXB4IDExcHggcmdiYSgwLDAsMCwwLjYyKTsNCgkJfQ0KCQ0KCQlwcmUgew0KCQkJZGlzcGxheTogYmxvY2s7DQoJCQlmb250LWZhbWlseTogbW9ub3NwYWNlOw0KCQkJd2hpdGUtc3BhY2U6IHByZTsNCgkJCW1hcmdpbjogMDsNCgkJfQ0KCQ0KCQkjaGVhZGVyIHsNCgkJCWhlaWdodDogMTcwcHg7DQoJCQl3aWR0aDogMTAwJTsNCgkJCWZvbnQtZmFtaWx5OiBtb25vc3BhY2U7DQoJCQljb2xvcjogd2hpdGU7DQoJCQl0ZXh0LWFsaWduOiBjZW50ZXI7DQoJCQkvKiBiYWNrZ3JvdW5kOiAjMWMxYzFjOyAqLw0KCQkJYmFja2dyb3VuZDogcmdiKDQzLDQzLDQzKTsNCgkJCWJhY2tncm91bmQ6IGxpbmVhci1ncmFkaWVudCgxODBkZWcsIHJnYmEoNDMsNDMsNDMsMSkgMCUsIHJnYmEoNTYsNTYsNTYsMSkgMzUlLCByZ2JhKDc0LDc0LDc0LDEpIDEwMCUpOw0KCQkJbWFyZ2luOiAwOw0KCQkJcGFkZGluZzogMDsNCgkJfQ0KCQ0KCQkjZG93bmxvYWRJbmZvIHsNCgkJCW1hcmdpbjogMDsNCgkJCXBhZGRpbmc6IDEwcHg7DQoJCQlib3JkZXItYm90dG9tOiAxcHggc29saWQgI2MwYzBjMDsNCgkJCWJvcmRlci1sZWZ0OiAxcHggc29saWQgI2MwYzBjMDsNCgkJCWJvcmRlci1yaWdodDogMXB4IHNvbGlkICNjMGMwYzA7DQoJCX0NCgkJDQoJCS5kb3dubG9hZF90aXRsZSB7DQoJCQlmb250LWZhbWlseTogbW9ub3NwYWNlOw0KCQkJY29sb3I6IHdoaXRlOw0KCQkJZm9udC1zaXplOiAyMnB4Ow0KCQkJdGV4dC1hbGlnbjogY2VudGVyOw0KCQkJbWFyZ2luOiAwIDAgNXB4IDA7DQoJCX0NCgkNCgkJI2RhdGEgew0KCQkJd2lkdGg6IDEwMCU7DQoJCQloZWlnaHQ6IDEwMHZoOw0KCQkJbWFyZ2luOiAwOw0KCQkJcGFkZGluZzogMDsNCgkJfQ0KCQ0KCQkjc2ZkbEZpbGVzIHsNCgkJCXdpZHRoOiAxMDAlOw0KCQkJaGVpZ2h0OiAxMDBweDsNCgkJCW1hcmdpbjogMDsNCgkJCXBhZGRpbmc6IDA7DQoJCQlib3JkZXItYm90dG9tOiAxcHggc29saWQgI2MwYzBjMDsNCgkJCWJhY2tncm91bmQtY29sb3I6ICMzMjMyMzI7DQoJCQl0ZXh0LWFsaWduOiBsZWZ0Ow0KCQkJZGlzcGxheTogbm9uZTsNCgkJCWZvbnQtZmFtaWx5OiBtb25vc3BhY2U7DQoJCQlmb250LXdlaWdodDogbm9ybWFsOw0KCQkJb3ZlcmZsb3c6IGF1dG87DQoJCX0NCgkJDQoJCS5zZmRsRmlsZXNMaW5lIHsNCgkJCW1hcmdpbjogMDsNCgkJCXBhZGRpbmc6IDAgM3B4IDAgM3B4Ow0KCQl9DQoJDQoJCSNsb2dCb3ggew0KCQkJd2lkdGg6IDEwMCU7DQoJCQloZWlnaHQ6IDEwMHB4Ow0KCQkJbWFyZ2luOiAwOw0KCQkJcGFkZGluZzogMDsNCgkJCWJvcmRlci1ib3R0b206IDFweCBzb2xpZCAjYzBjMGMwOw0KCQkJYmFja2dyb3VuZC1jb2xvcjogIzMyMzIzMjsNCgkJCXRleHQtYWxpZ246IGxlZnQ7DQoJCQlkaXNwbGF5OiBibG9jazsNCgkJCWZvbnQtZmFtaWx5OiBtb25vc3BhY2U7DQoJCQlmb250LXdlaWdodDogbm9ybWFsOw0KCQkJb3ZlcmZsb3c6IGF1dG87DQoJCX0NCgkJDQoJCS5sb2dCb3hMaW5lIHsNCgkJCW1hcmdpbjogMDsNCgkJCXBhZGRpbmc6IDAgM3B4IDAgM3B4Ow0KCQkJYm9yZGVyLWJvdHRvbTogMXB4IGRhc2hlZCAjYzBjMGMwOw0KCQl9DQoJCQ0KCQkubG9nQm94TGluZTpudGgtY2hpbGQob2RkKSB7DQoJCQliYWNrZ3JvdW5kLWNvbG9yOiAjMmIyYjJiOw0KCQl9DQoJCQ0KCQkuZmlsZXMgew0KCQkJZGlzcGxheTogZmxleDsNCgkJCW1hcmdpbjogMDsNCgkJCWJvcmRlci1ib3R0b206IDFweCBzb2xpZCAjYzBjMGMwOw0KCQkJZm9udC1mYW1pbHk6IEFyaWFsLCBIZWx2ZXRpY2EsIHNhbnMtc2VyaWY7DQoJCQlmb250LXNpemU6IDE0cHg7DQoJCQl2ZXJ0aWNhbC1hbGlnbjogbWlkZGxlOw0KCQkJcGFkZGluZzogM3B4Ow0KCQl9DQoJCQ0KCQkuZmlsZXM6bnRoLWNoaWxkKG9kZCkgew0KCQkJYmFja2dyb3VuZC1jb2xvcjogIzMyMzIzMjsNCgkJfQ0KCQ0KCQkuZmlsZXNfbmFtZSB7DQoJCQlmbGV4OiA0Ow0KCQkJd2lkdGg6IDEwMCU7DQoJCX0NCgkJDQoJCS5maWxlc19wcm9ncmVzc2JhciB7DQoJCQlmbGV4OiAwOw0KCQkJbWluLXdpZHRoOiAxNTBweDsNCgkJCWJhY2tncm91bmQ6IGdyYXk7DQoJCQl3aGl0ZS1zcGFjZTogbm93cmFwOw0KCQkJYm9yZGVyLWJvdHRvbTogMXB4IHNvbGlkICNjMGMwYzA7DQoJCQlmb250LWZhbWlseTogQXJpYWwsIEhlbHZldGljYSwgc2Fucy1zZXJpZjsNCgkJCWZvbnQtc2l6ZTogMTRweDsNCgkJCXZlcnRpY2FsLWFsaWduOiBtaWRkbGU7DQoJCX0NCgkJDQoJCS5maWxlc19wcm9ncmVzcyB7DQoJCQliYWNrZ3JvdW5kOiB3aGl0ZTsNCgkJCWZvbnQtd2VpZ2h0OiBib2xkOw0KCQkJdGV4dC1hbGlnbjogY2VudGVyOw0KCQkJY29sb3I6IGJsYWNrOw0KCQl9DQoJCQ0KCQkuZmlsZXNfbG9hZGVkIHsNCgkJCWZsZXg6IDA7DQoJCQl3aGl0ZS1zcGFjZTogbm93cmFwOw0KCQkJdGV4dC1hbGlnbjogcmlnaHQ7DQoJCQlwYWRkaW5nOiAwIDVweCAwIDVweDsNCgkJCW1pbi13aWR0aDogMTUwcHg7DQoJCX0NCgkJDQoJCS5tYWluX2J1dHRvbnMgew0KCQkJd2lkdGg6IDEwMCU7DQoJCQliYWNrZ3JvdW5kOiAjNjk2OTY5Ow0KCQkJd2hpdGUtc3BhY2U6IG5vd3JhcDsNCgkJCXRleHQtYWxpZ246IGNlbnRlcjsNCgkJfQ0KCQkNCgkJLmJ1dHRvbiB7DQoJCQlib3JkZXItcmFkaXVzOiA4cHg7DQoJCQljb2xvcjogd2hpdGU7DQoJCQlwYWRkaW5nOiA4cHggMThweDsNCgkJCXRleHQtYWxpZ246IGNlbnRlcjsNCgkJCXRleHQtZGVjb3JhdGlvbjogbm9uZTsNCgkJCWRpc3BsYXk6IGlubGluZS1ibG9jazsNCgkJCWZvbnQtc2l6ZTogMTZweDsNCgkJCWZvbnQtZmFtaWx5OiBBcmlhbCwgSGVsdmV0aWNhLCBzYW5zLXNlcmlmOw0KCQkJbWFyZ2luOiA0cHggMnB4Ow0KCQkJY3Vyc29yOiBwb2ludGVyOw0KCQl9DQoJCQ0KCQkuYnV0dG9uX2dyZWVuIHsNCgkJCWJhY2tncm91bmQtY29sb3I6ICMwNEFBNkQ7DQoJCQljb2xvcjogd2hpdGU7IA0KCQkJYm9yZGVyOiAycHggc29saWQgd2hpdGU7DQoJCQlkaXNwbGF5OiBub25lOw0KCQl9DQoJCS5idXR0b25fZ3JlZW46aG92ZXIgew0KCQkJYmFja2dyb3VuZC1jb2xvcjogd2hpdGU7DQoJCQljb2xvcjogYmxhY2s7DQoJCX0NCgkJDQoJCS5idXR0b25fcmVkIHsNCgkJCWJhY2tncm91bmQtY29sb3I6ICNmNDQzMzY7DQoJCQljb2xvcjogd2hpdGU7IA0KCQkJYm9yZGVyOiAycHggc29saWQgd2hpdGU7DQoJCQlkaXNwbGF5OiBub25lOw0KCQl9DQoJCS5idXR0b25fcmVkOmhvdmVyIHsNCgkJCWJhY2tncm91bmQtY29sb3I6IHdoaXRlOw0KCQkJY29sb3I6IGJsYWNrOw0KCQl9DQoJCQ0KCQkuYnV0dG9uX2JsdWUgew0KCQkJYmFja2dyb3VuZC1jb2xvcjogIzAwOENCQTsNCgkJCWNvbG9yOiB3aGl0ZTsgDQoJCQlib3JkZXI6IDJweCBzb2xpZCB3aGl0ZTsNCgkJfQ0KCQkuYnV0dG9uX2JsdWU6aG92ZXIgew0KCQkJYmFja2dyb3VuZC1jb2xvcjogd2hpdGU7DQoJCQljb2xvcjogYmxhY2s7DQoJCX0NCgkJDQoJCSNmaWxlSW5wdXQgew0KICAgICAgICAgICAgZGlzcGxheTogbm9uZTsNCiAgICAgICAgfQ0KCQkNCgkJLnJlc2l6YWJsZS1ib3ggew0KICAgICAgICAgICAgd2lkdGg6IDEwMCU7DQogICAgICAgICAgICBtaW4taGVpZ2h0OiAxMDBweDsNCiAgICAgICAgICAgIHJlc2l6ZTogdmVydGljYWw7DQogICAgICAgICAgICBvdmVyZmxvdzogYXV0bzsNCiAgICAgICAgfQ0KCQkNCgkJQG1lZGlhIChtYXgtd2lkdGg6IDc2N3B4KSB7DQoJCQkjbG9hZGVyIHsNCgkJCQl3aWR0aDogMTAwJTsNCgkJCX0NCgkJfQ0KICAgIDwvc3R5bGU+DQo8L2hlYWQ+DQo8Ym9keT4NCg0KICAgIDxkaXYgaWQ9ImxvYWRlciI+DQogICAgICAgIDxkaXYgaWQ9ImhlYWRlciI+DQoJCQk8cHJlPg0KICAgICAgICAgICAgICAgICAgX19fX18gX19fX19fIF9fX19fICBfICAgICAgIF9fX19fICAgICAgICAgICAgICAgICAgICAgICAgICAgICANCiAgICAgICAgICAgICAgICAgLyBfX19ffCAgX19fX3wgIF9fIFx8IHwgICAgIC8gX19fX3wgICAgICAgICAgICAgICAgICAgICAgICAgICAgDQogICAgIF8gX18gIF8gICBffCAoX19fIHwgfF9fICB8IHwgIHwgfCB8ICAgIHwgKF9fXyAgIF9fIF8gXyAgIF8gIF9fIF8gIF9fXyBfIF9fIA0KICAgIHwgJ18gXHwgfCB8IHxcX19fIFx8ICBfX3wgfCB8ICB8IHwgfCAgICAgXF9fXyBcIC8gX2AgfCB8IHwgfC8gX2AgfC8gXyBcICdfX3wNCiAgICB8IHxfKSB8IHxffCB8X19fXykgfCB8ICAgIHwgfF9ffCB8IHxfX19fIF9fX18pIHwgKF98IHwgfF98IHwgKF98IHwgIF9fLyB8ICAgDQogICAgfCAuX18vIFxfXywgfF9fX19fL3xffCAgICB8X19fX18vfF9fX19fX3xfX19fXy8gXF9fLF98XF9fLF98XF9fLCB8XF9fX3xffCAgIA0KICAgIHwgfCAgICAgX18vIHwgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBfXy8gfCAgICAgICAgICANCiAgICB8X3wgICAgfF9fXy8gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICB8X19fLyAgICAgICAgICAgDQoJCQk8L3ByZT4NCgkJPC9kaXY+DQoNCgkJPGRpdiBjbGFzcz0ibWFpbl9idXR0b25zIj4NCgkJCTxidXR0b24gaWQ9InN0YXJ0QnV0dG9uIiBjbGFzcz0iYnV0dG9uIGJ1dHRvbl9ncmVlbiIgb25jbGljaz0ic2VuZE1lc3NhZ2UoJ3N0YXJ0JykiPlN0YXJ0PC9idXR0b24+DQoJCQk8YnV0dG9uIGlkPSJzdG9wQnV0dG9uIiBjbGFzcz0iYnV0dG9uIGJ1dHRvbl9yZWQiIG9uY2xpY2s9InNlbmRNZXNzYWdlKCdzdG9wJykiPlN0b3A8L2J1dHRvbj4NCgkJCTxsYWJlbCBmb3I9ImZpbGVJbnB1dCIgY2xhc3M9ImJ1dHRvbiBidXR0b25fYmx1ZSIgaWQ9ImZpbGVJbnB1dExhYmVsIj5TZWxlY3QgU0ZETCBmaWxlIC4uLjwvbGFiZWw+DQoJCQk8aW5wdXQgdHlwZT0iZmlsZSIgaWQ9ImZpbGVJbnB1dCIgb25jaGFuZ2U9InVwZGF0ZUZpbGVOYW1lKCkiIC8+DQoJCQk8YnV0dG9uIGNsYXNzPSJidXR0b24gYnV0dG9uX2JsdWUiIG9uY2xpY2s9InVwbG9hZEZpbGUoKSI+VXBsb2FkPC9idXR0b24+DQoJCTwvZGl2Pg0KCQkNCgkJPGRpdiBjbGFzcz0icmVzaXphYmxlLWJveCIgaWQ9ImxvZ0JveCI+PC9kaXY+DQoJCTwhLS0gPGRpdiBpZD0ic2ZkbEZpbGVzIj48L2Rpdj4gLS0+DQoJCTxkaXYgaWQ9InJsc2RhdGEiPjwvZGl2Pg0KICAgICAgICA8ZGl2IGlkPSJkYXRhIj48L2Rpdj4NCiAgICA8L2Rpdj4NCg0KCTxzY3JpcHQ+DQoJCWZ1bmN0aW9uIGZvcm1hdEJ5dGVzRGVjaW1hbChieXRlcywgZGVjaW1hbHMgPSAyKSB7DQoJCQlpZiAoYnl0ZXMgPT09IDApIHJldHVybiAnMCBCeXRlcyc7DQoJCQljb25zdCBrID0gMTAwMDsNCgkJCWNvbnN0IHNpemVzID0gWydCeXRlcycsICdLQicsICdNQicsICdHQicsICdUQicsICdQQicsICdFQicsICdaQicsICdZQiddOw0KCQkJY29uc3QgaSA9IE1hdGguZmxvb3IoTWF0aC5sb2coYnl0ZXMpIC8gTWF0aC5sb2coaykpOw0KCQkJcmV0dXJuIHBhcnNlRmxvYXQoKGJ5dGVzIC8gTWF0aC5wb3coaywgaSkpLnRvRml4ZWQoZGVjaW1hbHMpKSArICcgJyArIHNpemVzW2ldOw0KCQl9DQoJCQ0KCQlmdW5jdGlvbiBpc0R1cGxpY2F0ZShsb2dUZXh0KSB7DQoJCQljb25zdCBtZXNzYWdlQm94ID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoImxvZ0JveCIpOw0KCQkJY29uc3QgZXhpc3RpbmdMb2dzID0gbWVzc2FnZUJveC5nZXRFbGVtZW50c0J5Q2xhc3NOYW1lKCJsb2dCb3hMaW5lIik7DQoJCQlmb3IgKGNvbnN0IGV4aXN0aW5nTG9nIG9mIGV4aXN0aW5nTG9ncykgew0KCQkJCWlmIChleGlzdGluZ0xvZy50ZXh0Q29udGVudCA9PT0gbG9nVGV4dCkgew0KCQkJCQlyZXR1cm4gdHJ1ZTsNCgkJCQl9DQoJCQl9DQoJCQlyZXR1cm4gZmFsc2U7DQoJCX0NCg0KCQlmdW5jdGlvbiBhZGRMb2cobG9nVGV4dCkgew0KCQkJaWYgKCFpc0R1cGxpY2F0ZShsb2dUZXh0KSkgew0KCQkJCWNvbnN0IG1lc3NhZ2VCb3ggPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgibG9nQm94Iik7DQoJCQkJbWVzc2FnZUJveC5pbm5lckhUTUwgKz0gJzxwIGNsYXNzPSJsb2dCb3hMaW5lIj4nICsgbG9nVGV4dCArICc8L3A+JzsNCgkJCQltZXNzYWdlQm94LnNjcm9sbFRvcCA9IG1lc3NhZ2VCb3guc2Nyb2xsSGVpZ2h0Ow0KCQkJfQ0KCQl9DQoJCQ0KCQlmdW5jdGlvbiBhZGRMb2dFcnJvcihsb2dUZXh0KSB7DQoJCQlpZiAoIWlzRHVwbGljYXRlKGxvZ1RleHQpKSB7DQoJCQkJY29uc3QgbWVzc2FnZUJveCA9IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJsb2dCb3giKTsNCgkJCQltZXNzYWdlQm94LmlubmVySFRNTCArPSAnPHAgY2xhc3M9ImxvZ0JveExpbmUiIHN0eWxlPSJjb2xvcjogcmVkOyI+JyArIGxvZ1RleHQgKyAnPC9wPic7DQoJCQkJbWVzc2FnZUJveC5zY3JvbGxUb3AgPSBtZXNzYWdlQm94LnNjcm9sbEhlaWdodDsNCgkJCX0NCgkJfQ0KDQoJCWxldCBzb2NrZXQ7DQoJCQ0KCQlmdW5jdGlvbiBzdGFydFdlYlNvY2tldCgpIHsNCgkJCXNvY2tldCA9IG5ldyBXZWJTb2NrZXQoIndzOi8ve3sgaG9zdCB9fTp7eyB3c19wb3J0IH19Iik7DQoNCgkJCXNvY2tldC5vbm9wZW4gPSBmdW5jdGlvbiAoKSB7DQoJCQkJY29uc29sZS5sb2coIldlYlNvY2tldCBjb25uZWN0ZWQhIik7DQoJCQkJYWRkTG9nKCdXZWJTb2NrZXQgY29ubmVjdGVkIScpOw0KCQkJfTsNCg0KCQkJc29ja2V0Lm9ubWVzc2FnZSA9IGZ1bmN0aW9uIChldmVudCkgew0KCQkJCS8vIGNvbnNvbGUubG9nKGV2ZW50LmRhdGEpDQoNCgkJCQl0cnkgew0KCQkJCQljb25zdCBkYXRhID0gSlNPTi5wYXJzZShldmVudC5kYXRhKTsNCg0KCQkJCQlpZiAoQXJyYXkuaXNBcnJheShkYXRhKSAmJiBkYXRhLmxlbmd0aCA9PT0gMSAmJiBBcnJheS5pc0FycmF5KGRhdGFbMF0pICYmIGRhdGFbMF0ubGVuZ3RoID49IDUpIHsNCgkJCQkJCWNvbnN0IGRvd25sb2FkSW5mbyA9IGRhdGFbMF0uc2xpY2UoMCwgNCk7DQoJCQkJCQljb25zdCBmaWxlcyA9IGRhdGFbMF1bNF07DQoJCQkJCQkNCgkJCQkJCWNvbnN0IGRvd25sb2FkTmFtZSA9IGRvd25sb2FkSW5mb1swXQ0KCQkJCQkJY29uc3QgZG93bmxvYWRTaXplID0gZm9ybWF0Qnl0ZXNEZWNpbWFsKGRvd25sb2FkSW5mb1sxXSkNCgkJCQkJCWNvbnN0IGRvd25sb2FkTG9hZGVkID0gZm9ybWF0Qnl0ZXNEZWNpbWFsKGRvd25sb2FkSW5mb1syXSkNCgkJCQkJCWNvbnN0IGRvd25sb2FkUHJvZ3Jlc3MgPSBkb3dubG9hZEluZm9bM10NCgkJCQkJCQ0KCQkJCQkJY29uc3QgZG93bmxvYWRJbmZvQm94ID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoInJsc2RhdGEiKTsNCgkJCQkJCWRvd25sb2FkSW5mb0JveC5pbm5lckhUTUwgPSBgDQoJCQkJCQkJPGRpdiBpZD0iZG93bmxvYWRJbmZvIj4NCgkJCQkJCQkJPGRpdiBjbGFzcz0iZG93bmxvYWRfdGl0bGUiPiR7ZG93bmxvYWROYW1lfTwvZGl2Pg0KCQkJCQkJCQk8ZGl2IGNsYXNzPSJmaWxlc19wcm9ncmVzc2JhciI+PGRpdiBjbGFzcz0iZmlsZXNfcHJvZ3Jlc3MiIHN0eWxlPSJ3aWR0aDoke2Rvd25sb2FkUHJvZ3Jlc3N9JSI+JHtkb3dubG9hZFByb2dyZXNzfSUgKCR7ZG93bmxvYWRMb2FkZWR9IC8gJHtkb3dubG9hZFNpemV9KTwvZGl2PjwvZGl2Pg0KCQkJCQkJCTwvZGl2Pg0KCQkJCQkJYDsNCgkJCQkJCQ0KCQkJCQkJY29uc3QgZmlsZXNCb3ggPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgiZGF0YSIpOw0KCQkJCQkJZmlsZXNCb3guaW5uZXJIVE1MID0gJyc7DQoJCQkJCQlmaWxlc0JveC5zdHlsZS5kaXNwbGF5ID0gImJsb2NrIjsNCg0KCQkJCQkJZmlsZXMuZm9yRWFjaChmaWxlSW5mbyA9PiB7DQoJCQkJCQkJaWYgKEFycmF5LmlzQXJyYXkoZmlsZUluZm8pICYmIGZpbGVJbmZvLmxlbmd0aCA+PSA0KSB7DQoJCQkJCQkJCWNvbnN0IGZpbGVOYW1lID0gZmlsZUluZm9bMF07DQoJCQkJCQkJCWNvbnN0IGZpbGVTaXplID0gZm9ybWF0Qnl0ZXNEZWNpbWFsKGZpbGVJbmZvWzFdKTsNCgkJCQkJCQkJY29uc3QgZG93bmxvYWRlZCA9IGZvcm1hdEJ5dGVzRGVjaW1hbChmaWxlSW5mb1syXSk7DQoJCQkJCQkJCWNvbnN0IHByb2dyZXNzID0gZmlsZUluZm9bM107DQoJCQkJCQkJCQ0KCQkJCQkJCQljb25zdCBmaWxlTGluZSA9IGANCgkJCQkJCQkJCTxkaXYgY2xhc3M9ImZpbGVzIj4NCgkJCQkJCQkJCQk8ZGl2IGNsYXNzPSJmaWxlc19uYW1lIj4ke2ZpbGVOYW1lfTwvZGl2Pg0KCQkJCQkJCQkJCTxkaXYgY2xhc3M9ImZpbGVzX3Byb2dyZXNzYmFyIj48ZGl2IGNsYXNzPSJmaWxlc19wcm9ncmVzcyIgc3R5bGU9IndpZHRoOiR7cHJvZ3Jlc3N9JSI+JHtwcm9ncmVzc30lPC9kaXY+PC9kaXY+DQoJCQkJCQkJCQkJPGRpdiBjbGFzcz0iZmlsZXNfbG9hZGVkIj4ke2Rvd25sb2FkZWR9IC8gJHtmaWxlU2l6ZX08L2Rpdj4NCgkJCQkJCQkJCTwvZGl2Pg0KCQkJCQkJCQlgOw0KCQkJCQkJCQkNCgkJCQkJCQkJZmlsZXNCb3guaW5uZXJIVE1MICs9IGZpbGVMaW5lOw0KCQkJCQkJCX0NCgkJCQkJCX0pOw0KCQkJCQl9IGVsc2Ugew0KCQkJCQkJdHJ5IHsNCgkJCQkJCQlkYXRhLmZvckVhY2gobG9nSW5mbyA9PiB7DQoJCQkJCQkJCWlmIChsb2dJbmZvLnN0YXJ0c1dpdGgoIkVycm9yIikpIHsNCgkJCQkJCQkJCWFkZExvZ0Vycm9yKGxvZ0luZm8pOw0KCQkJCQkJCQl9IGVsc2UgaWYgKGxvZ0luZm8uc3RhcnRzV2l0aCgiU3RhcnQgRG93bmxvYWQiKSkgew0KCQkJCQkJCQkJZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ3N0b3BCdXR0b24nKS5zdHlsZS5kaXNwbGF5ID0gJ2lubGluZS1ibG9jayc7DQoJCQkJCQkJCQlkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgnc3RhcnRCdXR0b24nKS5zdHlsZS5kaXNwbGF5ID0gJ25vbmUnOw0KCQkJCQkJCQl9IGVsc2UgaWYgKGxvZ0luZm8uc3RhcnRzV2l0aCgiU3RhcnRpbmcgZG93bmxvYWQiKSkgew0KCQkJCQkJCQkJZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ3N0b3BCdXR0b24nKS5zdHlsZS5kaXNwbGF5ID0gJ2lubGluZS1ibG9jayc7DQoJCQkJCQkJCQlkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgnc3RhcnRCdXR0b24nKS5zdHlsZS5kaXNwbGF5ID0gJ25vbmUnOw0KCQkJCQkJCQl9IGVsc2UgaWYgKGxvZ0luZm8uc3RhcnRzV2l0aCgiU3RvcHBpbmcgYWxsIGRvd25sb2FkcyIpKSB7DQoJCQkJCQkJCQlkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgnc3RvcEJ1dHRvbicpLnN0eWxlLmRpc3BsYXkgPSAnbm9uZSc7DQoJCQkJCQkJCQlkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgnc3RhcnRCdXR0b24nKS5zdHlsZS5kaXNwbGF5ID0gJ2lubGluZS1ibG9jayc7DQoJCQkJCQkJCX0gZWxzZSB7DQoJCQkJCQkJCQlhZGRMb2cobG9nSW5mbykNCgkJCQkJCQkJfQ0KCQkJCQkJCX0pOw0KCQkJCQkJfSBjYXRjaCAoZXJyb3IpIHsNCgkJCQkJCQljb25zb2xlLmVycm9yKCdEYXRhIGVycm9yOiAnLCBlcnJvcik7DQoJCQkJCQl9DQoJCQkJCQkNCgkJCQkJfQ0KCQkJCX0gY2F0Y2ggKGVycm9yKSB7DQoJCQkJCWNvbnNvbGUuZXJyb3IoJ0pTT04gZXJyb3I6ICcsIGVycm9yKTsNCgkJCQl9DQoJCQl9Ow0KDQoJCQlzb2NrZXQub25lcnJvciA9IGZ1bmN0aW9uIChlcnJvcikgew0KCQkJCWNvbnNvbGUuZXJyb3IoIldlYlNvY2tldCBlcnJvcjogIiwgZXJyb3IpOw0KCQkJCWFkZExvZ0Vycm9yKCJXZWJTb2NrZXQgZXJyb3I6ICIgKyBlcnJvci5tZXNzYWdlKTsNCgkJCX07DQoJCX0NCg0KICAgICAgICBmdW5jdGlvbiBzdG9wV2ViU29ja2V0KCkgew0KICAgICAgICAgICAgaWYgKHNvY2tldCkgew0KICAgICAgICAgICAgICAgIHNvY2tldC5jbG9zZSgpOw0KICAgICAgICAgICAgICAgIGNvbnNvbGUubG9nKCJXZWJTb2NrZXQgZGlzY29ubmVjdGVkISIpOw0KCQkJCWFkZExvZygiV2ViU29ja2V0IGRpc2Nvbm5lY3RlZCEiKTsNCiAgICAgICAgICAgIH0NCiAgICAgICAgfQ0KDQogICAgICAgIGZ1bmN0aW9uIHNlbmRNZXNzYWdlKG1lc3NhZ2UpIHsNCiAgICAgICAgICAgIGlmIChzb2NrZXQgJiYgc29ja2V0LnJlYWR5U3RhdGUgPT09IFdlYlNvY2tldC5PUEVOKSB7DQogICAgICAgICAgICAgICAgY29uc3QgbWVzc2FnZURhdGEgPSB7DQogICAgICAgICAgICAgICAgICAgIGNvbW1hbmQ6IG1lc3NhZ2UNCiAgICAgICAgICAgICAgICB9Ow0KICAgICAgICAgICAgICAgIGNvbnN0IGpzb25NZXNzYWdlID0gSlNPTi5zdHJpbmdpZnkobWVzc2FnZURhdGEpOw0KICAgICAgICAgICAgICAgIHNvY2tldC5zZW5kKGpzb25NZXNzYWdlKTsNCiAgICAgICAgICAgIH0NCiAgICAgICAgfQ0KDQoJCWZ1bmN0aW9uIHVwZGF0ZUZpbGVOYW1lKCkgew0KICAgICAgICAgICAgY29uc3QgaW5wdXQgPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgnZmlsZUlucHV0Jyk7DQogICAgICAgICAgICBjb25zdCBsYWJlbCA9IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdmaWxlSW5wdXRMYWJlbCcpOw0KICAgICAgICAgICAgY29uc3QgZmlsZU5hbWUgPSBpbnB1dC5maWxlc1swXSA/IGlucHV0LmZpbGVzWzBdLm5hbWUgOiAnU2VsZWN0IFNGREwgZmlsZSAuLi4nOw0KICAgICAgICAgICAgbGFiZWwudGV4dENvbnRlbnQgPSBmaWxlTmFtZTsNCiAgICAgICAgfQ0KDQoJCWZ1bmN0aW9uIHJlc2V0RmlsZUlucHV0KCkgew0KCQkJY29uc3QgZmlsZUlucHV0ID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ2ZpbGVJbnB1dCcpOw0KCQkJZmlsZUlucHV0LnZhbHVlID0gJyc7DQoJCQl1cGRhdGVGaWxlTmFtZSgpOw0KCQl9DQoNCiAgICAgICAgZnVuY3Rpb24gdXBsb2FkRmlsZSgpIHsNCiAgICAgICAgICAgIGNvbnN0IGZpbGVJbnB1dCA9IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJmaWxlSW5wdXQiKTsNCiAgICAgICAgICAgIGNvbnN0IGZpbGUgPSBmaWxlSW5wdXQuZmlsZXNbMF07DQoNCiAgICAgICAgICAgIGlmIChmaWxlKSB7DQogICAgICAgICAgICAgICAgY29uc3QgcmVhZGVyID0gbmV3IEZpbGVSZWFkZXIoKTsNCiAgICAgICAgICAgICAgICByZWFkZXIub25sb2FkID0gZnVuY3Rpb24gKGUpIHsNCiAgICAgICAgICAgICAgICAgICAgY29uc3QgY29udGVudCA9IGUudGFyZ2V0LnJlc3VsdDsNCiAgICAgICAgICAgICAgICAgICAgaWYgKHNvY2tldCAmJiBzb2NrZXQucmVhZHlTdGF0ZSA9PT0gV2ViU29ja2V0Lk9QRU4pIHsNCiAgICAgICAgICAgICAgICAgICAgICAgIGNvbnN0IGZpbGVJbmZvID0gew0KICAgICAgICAgICAgICAgICAgICAgICAgICAgIG9yaWdpbmFsX2ZpbGVuYW1lOiBmaWxlLm5hbWUsDQogICAgICAgICAgICAgICAgICAgICAgICAgICAgY29udGVudDogY29udGVudA0KICAgICAgICAgICAgICAgICAgICAgICAgfTsNCiAgICAgICAgICAgICAgICAgICAgICAgIGNvbnN0IGpzb25NZXNzYWdlID0gSlNPTi5zdHJpbmdpZnkoZmlsZUluZm8pOw0KICAgICAgICAgICAgICAgICAgICAgICAgc29ja2V0LnNlbmQoanNvbk1lc3NhZ2UpOw0KCQkJCQkJcmVzZXRGaWxlSW5wdXQoKTsNCiAgICAgICAgICAgICAgICAgICAgfQ0KICAgICAgICAgICAgICAgIH07DQogICAgICAgICAgICAgICAgcmVhZGVyLnJlYWRBc1RleHQoZmlsZSk7DQogICAgICAgICAgICB9IGVsc2Ugew0KICAgICAgICAgICAgICAgIGFsZXJ0KCJTZWxlY3QgU0ZETCB0byB1cGxvYWQuLi4iKTsNCiAgICAgICAgICAgIH0NCiAgICAgICAgfQ0KCQkNCiAgICAgICAgc3RhcnRXZWJTb2NrZXQoKTsNCgkJDQoJCWxldCBpc1Jlc2l6aW5nID0gZmFsc2U7DQoNCgkJZnVuY3Rpb24gc3RhcnRSZXNpemluZyhlKSB7DQoJCQlpc1Jlc2l6aW5nID0gdHJ1ZTsNCgkJCWRvY3VtZW50LmFkZEV2ZW50TGlzdGVuZXIoJ21vdXNlbW92ZScsIGhhbmRsZU1vdXNlTW92ZSk7DQoJCQlkb2N1bWVudC5hZGRFdmVudExpc3RlbmVyKCdtb3VzZXVwJywgc3RvcFJlc2l6aW5nKTsNCgkJfQ0KDQoJCWZ1bmN0aW9uIGhhbmRsZU1vdXNlTW92ZShlKSB7DQoJCQlpZiAoaXNSZXNpemluZykgew0KCQkJCWNvbnN0IHJlc2l6YWJsZUJveCA9IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdsb2dCb3gnKTsNCgkJCQljb25zdCBuZXdIZWlnaHQgPSBlLmNsaWVudFkgLSByZXNpemFibGVCb3guZ2V0Qm91bmRpbmdDbGllbnRSZWN0KCkudG9wOw0KCQkJCXJlc2l6YWJsZUJveC5zdHlsZS5oZWlnaHQgPSBNYXRoLm1heChuZXdIZWlnaHQsIDEwMCkgKyAncHgnOw0KCQkJfQ0KCQl9DQoNCgkJZnVuY3Rpb24gc3RvcFJlc2l6aW5nKCkgew0KCQkJaXNSZXNpemluZyA9IGZhbHNlOw0KCQkJZG9jdW1lbnQucmVtb3ZlRXZlbnRMaXN0ZW5lcignbW91c2Vtb3ZlJywgaGFuZGxlTW91c2VNb3ZlKTsNCgkJCWRvY3VtZW50LnJlbW92ZUV2ZW50TGlzdGVuZXIoJ21vdXNldXAnLCBzdG9wUmVzaXppbmcpOw0KCQl9DQogICAgPC9zY3JpcHQ+DQo8L2JvZHk+DQo8L2h0bWw+DQpQSwMEFAAAAAAAVZdnWH55H9QzCAAAMwgAAAgAAAA0MDQuaHRtbDwhRE9DVFlQRSBodG1sPg0KPGh0bWwgbGFuZz0iZW4iPg0KPGhlYWQ+DQogICAgPG1ldGEgY2hhcnNldD0iVVRGLTgiPg0KICAgIDxtZXRhIGh0dHAtZXF1aXY9IlgtVUEtQ29tcGF0aWJsZSIgY29udGVudD0iSUU9ZWRnZSI+DQogICAgPG1ldGEgbmFtZT0idmlld3BvcnQiIGNvbnRlbnQ9IndpZHRoPWRldmljZS13aWR0aCwgaW5pdGlhbC1zY2FsZT0xLjAiPg0KICAgIDx0aXRsZT5weVNGRExTYXVnZXIgV2ViLUdVSSAtIEVycm9yIDQwNCAoTm90IEZvdW5kKTwvdGl0bGU+DQogICAgPHN0eWxlPg0KCQlib2R5IHsNCgkJCWZvbnQtc2l6ZTogMTZweDsNCgkJCWJhY2tncm91bmQ6ICMyYjJiMmI7DQoJCQljb2xvcjogd2hpdGU7DQoJCQltYXJnaW46IDA7DQoJCQlwYWRkaW5nOiAwOw0KICAgICAgICAgICAgZGlzcGxheTogZmxleDsNCiAgICAgICAgICAgIGFsaWduLWl0ZW1zOiBjZW50ZXI7DQogICAgICAgICAgICBqdXN0aWZ5LWNvbnRlbnQ6IGNlbnRlcjsNCiAgICAgICAgICAgIG1pbi1oZWlnaHQ6IDEwMHZoOw0KCQl9DQoJDQoJCSNsb2FkZXIgew0KCQkJd2lkdGg6IDk5OXB4Ow0KICAgICAgICAgICAgYmFja2dyb3VuZC1jb2xvcjogIzI0MjQyNDsNCiAgICAgICAgICAgIGFsaWduLWl0ZW1zOiBjZW50ZXI7DQogICAgICAgICAgICBwYWRkaW5nOiAwOw0KCQkJbWFyZ2luOiAwOw0KCQl9DQoJCQ0KCQkjaGVhZGVyIHsNCgkJCWhlaWdodDogMTY1cHg7DQoJCQl3aWR0aDogMTAwJTsNCgkJCWZvbnQtZmFtaWx5OiBtb25vc3BhY2U7DQoJCQljb2xvcjogd2hpdGU7DQoJCQl0ZXh0LWFsaWduOiBjZW50ZXI7DQoJCQliYWNrZ3JvdW5kOiAjMWMxYzFjOw0KCQkJbWFyZ2luOiAwOw0KCQkJcGFkZGluZzogMDsNCgkJfQ0KCQkNCgkJI2RhdGEgew0KCQkJd2lkdGg6IDEwMCU7DQoJCQloZWlnaHQ6IDEwMHZoOw0KCQkJbWFyZ2luOiAwOw0KCQkJcGFkZGluZzogMDsNCgkJfQ0KCQkNCgkJLmVycm9yNDA0IHsNCgkJCWZvbnQtc2l6ZTogMzBweDsNCgkJCXRleHQtYWxpZ246IGNlbnRlcjsNCgkJCWZvbnQtZmFtaWx5OiBBcmlhbCwgSGVsdmV0aWNhLCBzYW5zLXNlcmlmOw0KCQkJcGFkZGluZzogMTAwcHg7DQoJCX0NCgkJDQoJCUBtZWRpYSAobWF4LXdpZHRoOiA3NjdweCkgew0KCQkJI2xvYWRlciB7DQoJCQkJd2lkdGg6IDEwMCU7DQoJCQl9DQoJCX0NCiAgICA8L3N0eWxlPg0KPC9oZWFkPg0KPGJvZHk+DQoNCiAgICA8ZGl2IGlkPSJsb2FkZXIiPg0KICAgICAgICA8ZGl2IGlkPSJoZWFkZXIiPg0KCQkJPHByZT4NCiAgICAgICAgICAgICAgICAgIF9fX19fIF9fX19fXyBfX19fXyAgXyAgICAgICBfX19fXyAgICAgICAgICAgICAgICAgICAgICAgICAgICAgDQogICAgICAgICAgICAgICAgIC8gX19fX3wgIF9fX198ICBfXyBcfCB8ICAgICAvIF9fX198ICAgICAgICAgICAgICAgICAgICAgICAgICAgIA0KICAgICBfIF9fICBfICAgX3wgKF9fXyB8IHxfXyAgfCB8ICB8IHwgfCAgICB8IChfX18gICBfXyBfIF8gICBfICBfXyBfICBfX18gXyBfXyANCiAgICB8ICdfIFx8IHwgfCB8XF9fXyBcfCAgX198IHwgfCAgfCB8IHwgICAgIFxfX18gXCAvIF9gIHwgfCB8IHwvIF9gIHwvIF8gXCAnX198DQogICAgfCB8XykgfCB8X3wgfF9fX18pIHwgfCAgICB8IHxfX3wgfCB8X19fXyBfX19fKSB8IChffCB8IHxffCB8IChffCB8ICBfXy8gfCAgIA0KICAgIHwgLl9fLyBcX18sIHxfX19fXy98X3wgICAgfF9fX19fL3xfX19fX198X19fX18vIFxfXyxffFxfXyxffFxfXywgfFxfX198X3wgICANCiAgICB8IHwgICAgIF9fLyB8ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgX18vIHwgICAgICAgICAgDQogICAgfF98ICAgIHxfX18vICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgfF9fXy8gICAgICAgICAgIA0KCQkJPC9wcmU+DQoJCTwvZGl2Pg0KDQogICAgICAgIDxkaXYgaWQ9ImRhdGEiPg0KCQkJPGRpdiBjbGFzcz0iZXJyb3I0MDQiPg0KCQkJCTxwPjQwNCAtIE5vdCBGb3VuZDwvcD4NCgkJCQk8cD57eyBlcnJvciB9fTwvcD4NCgkJCTwvZGl2Pg0KICAgICAgICA8L2Rpdj4NCiAgICA8L2Rpdj4NCg0KPC9ib2R5Pg0KPC9odG1sPg0KUEsBAhQAFAAAAAAAJphnWPcw0ny+MwAAvjMAAAoAAAAAAAAAAAAAALaBAAAAAGluZGV4Lmh0bWxQSwECFAAUAAAAAABVl2dYfnkf1DMIAAAzCAAACAAAAAAAAAAAAAAAtoHmMwAANDA0Lmh0bWxQSwUGAAAAAAIAAgBuAAAAPzwAAAAA
    """

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
            if __use_web_gui__: add_weg_gui_log(f'FTP Connection Error: {e}')
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
                        if __printdebug__:
                            if __use_web_gui__: add_weg_gui_log(f'Exclude file: {final_full_file_path}')
                    else:
                        self.files.append((final_full_file_path, size))
                        if __printdebug__: print(f" \033[91;1mFTP-Index file found: {final_full_file_path}\033[0m")
                        if __printdebug__:
                            if __use_web_gui__: add_weg_gui_log(f'Add file: {final_full_file_path}')
                # also index all sub-dirs
                elif data["type"] == "dir":
                    self.dummy_progressbar.set_description(f' \033[93;1mSub-Dir:\033[0m \033[92;1m{item}\033[0m')
                    if __printdebug__:
                        if __use_web_gui__: add_weg_gui_log(f'Sub-Dir: {item}')
                    subdirectory_path = os.path.normpath(item).replace(os.sep, '/')
                    if __printdebug__: print(f" \033[91;1mFTP-Index found sub-dir: {subdirectory_path}\033[0m")
                    try:
                        self.list_files(subdirectory_path)
                    except Exception as e:
                        if __printdebug__: print(f" \033[91;1mError: FTP list subdir: {subdirectory_path} {e}\033[0m")
                        pass
        except Exception as e:
            if __printdebug__: print(f" \033[91;1mFTP Error: {e}\033[0m")
            if __use_web_gui__: add_weg_gui_log(f'FTP Error: {e}')
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
        self.stop_download = False

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
            if __use_web_gui__: add_weg_gui_log(f'Speedreport created: {speedreport}')
        except Exception as e:
            print(f" \033[91;1mError creating speedreport file: {speedreport} {e}\033[0m")
            if __use_web_gui__: add_weg_gui_log(f'Error creating speedreport file: {speedreport} {e}')

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
                if __use_web_gui__: add_weg_gui_log('Moving SFDL to download path!')
            shutil.move(file_path, dest_path)
        except Exception as e:
            print(f" \033[91;1mError: Can't move SFDL to download folder: {e}\033[0m")
            if __use_web_gui__: add_weg_gui_log(f"Error: Can't move SFDL to download folder: {e}")

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
        result = self.b2h(speed_bytes_per_sec, 1000)
        return result
    
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
                    if __use_web_gui__: add_weg_gui_log(f'[1] FTP Connection Error: {e}')
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
    
    @classmethod
    async def close_all_ftp_connections(cls, self_instance):
        global __download_running__
        self_instance.stop_download = True
        if __printdebug__: print(f" \033[91;1mStop download flag: {self_instance.stop_download}\033[0m")
        success = True
        if __download_running__:
            with self_instance.ftp_lock:
                for thread_id, session in list(self_instance.ftp_sessions.items()):
                    try:
                        if session:
                            if session is not None: session.quit()
                        del self_instance.ftp_sessions[thread_id]
                    except Exception as e:
                        if __printdebug__: print(f" \033[91;1mError closing FTP connection: {e}\033[0m")
                        if __use_web_gui__: add_weg_gui_log(f'Error closing FTP connection: {e}')
                        success = False
            if success:
                __download_running__ = False
                print(f" \033[93;1mAll FTP connections closed successfully.\033[0m")
                if __use_web_gui__: add_weg_gui_log(f'All FTP connections closed successfully.')
    
    def download_multiple_files(self, file_list):
        global __download_running__
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
            bar.clear()
            bar.close()
        
        self.bar.clear()
        self.bar.close()
        
        # move sfdl to download folder
        self.move_file(self.sfdl_file, self.download_folder)
        # get download time
        self.done_time = time.time() - self.start_time
        speed = self.calculate_download_speed(total_size, self.done_time)
        elapsed_time = self.seconds_to_readable_time(self.done_time)
        
        if __ftp_aborted__: # download was aborted
            print(f" \033[93;1mDownload aborted. Loaded for\033[0m \033[92;1m{elapsed_time} ({speed}/s)\033[0m")
            if __use_web_gui__: add_weg_gui_log(f'Download aborted. Loaded for {elapsed_time} ({speed}/s)')
            
            # create speedreport in download folder
            self.write_speedreport(self.local_download_path, self.release_name, f'Download aborted. Loaded {total_files} files in {elapsed_time} ({speed}/s)')
            
        else:
            print(f" \033[93;1mDownload completed in\033[0m \033[92;1m{elapsed_time} ({speed}/s)\033[0m")
            if __use_web_gui__: add_weg_gui_log(f'Download completed in {elapsed_time} ({speed}/s)')
            
            # create speedreport in download folder
            self.write_speedreport(self.local_download_path, self.release_name, f'Downloaded {total_files} files in {elapsed_time} ({speed}/s)')
            
            # use UnRAR to rextract RAR archives
            if __use_unrar__ is not None:
                rar_extractor = RarExtractor(self.local_download_path, self.local_download_path, password='')
                success = rar_extractor.extract_rar()
                if success:
                    print(f" \033[93;1mUnRAR ALL OK!\033[0m")
                    if __use_web_gui__: add_weg_gui_log('UnRAR ALL OK!')
        
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
                for bar in self.bars:
                    bar.refresh()
            else:
                self.bars[0].clear()
                self.bars[0].close()
            if __printdebug__: print(f" \033[93;1mDownloaded\033[0m \033[92;1m{local_file}\033[0m \033[93;1msuccessfully!\033[0m")

    def download_with_progress(self, ftp, remote_path, local_file, file_size, total_files, newBarIndex):
        if self.stop_download:
            if ftp is not None:
                ftp.close()
            return
        
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
                    if __use_web_gui__: add_weg_gui_log(f'[2] FTP Connection Error: {e}')
            finally:
                if ftp is not None:
                    ftp.close()

    def write_with_progress(self, data, local_filepath, remote_path, file_size, total_files, newBarIndex):
        if self.stop_download:
            return
        
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
                        if __use_web_gui__: self.update_web_file_array_info(len(data) + fileSize, remote_path)
                    else:
                        self.bars[newBarIndex].update(len(data))
                        self.bar.update(len(data))
                        if __use_web_gui__: self.update_web_file_array_info(len(data), remote_path)
        except Exception as e:
            print(f" \033[91;1mError can't write file: {e}\033[0m")
            if __use_web_gui__: add_weg_gui_log(f"Error can't write file: {e}")

    # update array for web-gui updates
    def update_web_file_array_info(self, g_loaded, f_name):
        global __web_gui_updates__
        f_name = os.path.basename(f_name) # file name only
        __web_gui_updates__[0][2] += g_loaded
        __web_gui_updates__[0][3] = int((__web_gui_updates__[0][2] / __web_gui_updates__[0][1]) * 100)
        for file in __web_gui_updates__[0][4]:
            if file[0] == f_name:
                file[2] += g_loaded
                file[3] = int((file[2] / file[1]) * 100)
                break
        
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
            if __use_web_gui__: add_weg_gui_log(f"Error: Can't read data from {sfdl_file}!")
            
        if all(variable is not None for variable in [ftp_host, ftp_port, ftp_path]):
            main(ftp_host, int(ftp_port), ftp_user, ftp_pass, ftp_path, self.destination, int(self.threads), release_name, proxy, sfdl_file)
        else:
            print(f" \033[91;1mError: Missing FTP data from SFDL file!\033[0m")
            if __use_web_gui__: add_weg_gui_log("Error: Missing FTP data from SFDL file!")
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
        if __ftp_aborted__ is not True:
            try:
                self.handler = WatcherHandler(directory_to_watch, password, destination, threads)
            except Exception as e:
                if __printdebug__: print(f" \033[91;1mError initializing WatcherHandler: {e}\033[0m")
                self.handler = None
            self.observer = Observer()
            self.observer_thread = None

    def start_watching(self):
        if self.handler:
            self.observer.schedule(self.handler, path=self.handler.directory_to_watch, recursive=True)
            self.observer.start()
            
            print(f" \033[93;1mpySFDLSauger watchdog is now running, automatic download service ready!\033[0m")
            print(f" \033[93;1mAdd new SFDL files in\033[0m \033[94;1m{self.handler.directory_to_watch}\033[0m \033[93;1mfor automatic downloads!\033[0m")
            if __use_web_gui__: add_weg_gui_log('pySFDLSauger watchdog is now running, automatic download service ready!')
            if __use_web_gui__: add_weg_gui_log(f'Add new SFDL files in {self.handler.directory_to_watch} for automatic downloads!')

            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.observer.stop()
                self.observer.join()
        else:
            if __printdebug__: print(f" \033[91;1mWatcherHandler initialization failed. Cannot start watching for new SFDL files.\033[0m")
        
    async def stop_watching(self):
        if getattr(self, 'running', False):
            self.running = False
            try:
                self.observer.stop()
                self.observer.join()
                __file_watcher__ = None
            except Exception as e:
                if __printdebug__: print(f" \033[91;1mError stopping FileWatcher: {e}\033[0m")

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
        subdirectories.append(os.path.normpath(root_path))
        def _list_subdirectories_recursive(current_path):
            nonlocal subdirectories
            for item in os.listdir(current_path):
                item_path = os.path.normpath(os.path.join(current_path, item))
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
                if __use_web_gui__: add_weg_gui_log(f'UnRAR error: Unable to remove: {rar_file}: {e}')

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
            if __use_web_gui__: add_weg_gui_log(f'UnRAR enter dir: {folder}')
            
            allRARFiles = self.find_all_rar_files(folder)
            firstRAR = self.find_rar_file(folder)
            
            if firstRAR is None:
                if __printdebug__: print(f" \033[91;1mUnRAR: No RAR file found in {folder}\033[0m")
                continue
            
            try:
                if not self.is_unrar_available():
                    if __use_web_gui__: add_weg_gui_log("UnRAR error: Can\'t find UnRAR executable! Please install UnRAR first!")
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
                    if __use_web_gui__: add_weg_gui_log('UnRAR error: ALL OK message NOT found!')
                    rar_errors += 1
                    pass
                else:
                    if __printdebug__: print(f" \033[93;1mUnRAR ALL OK ... remvoing RAR files ...\033[0m")
                    self.delete_rar_files(allRARFiles)
                    pass
            except Exception as e:
                print(f" \033[91;1mUnRAR error: {e}\033[0m")
                if __use_web_gui__: add_weg_gui_log(f'UnRAR error: {e}')
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

class WebSocketServer:
    def __init__(self, ip='127.0.0.1', port=8769, upload_directory=None):
        self.ip = ip
        self.port = port
        self.connected_clients = set()
        self.upload_directory = upload_directory
        
        os.makedirs(self.upload_directory, exist_ok=True)

    async def handle_client(self, websocket, path):
        try:
            self.connected_clients.add(websocket)
            if __printdebug__: print(f" \033[91;1mClient {websocket.remote_address} connected\033[0m")

            for client in self.connected_clients:
                if client != websocket:
                    if __printdebug__: print(f" \033[91;1mNew client connected: {websocket.remote_address}\033[0m")

            while True:
                message = await websocket.recv()
                if not message:
                    break
                if __printdebug__: print(f" \033[91;1mReceived message from {websocket.remote_address}: {message}\033[0m")

                try:
                    message_data = json.loads(message)
                    
                    if "command" in message_data:
                        command = message_data['command']
                        if command == "stop":
                            await self.stop_download()
                        if command == "start":
                            await self.start_download()
                    
                    if "original_filename" in message_data:
                        file_name = message_data['original_filename']
                        file_content = message_data['content']
                        file_path = os.path.join(self.upload_directory, f"{file_name}").replace('\\', '/')
                        await asyncio.to_thread(self.save_file, file_path, file_content)
                except json.decoder.JSONDecodeError as e:
                    if __printdebug__:
                        print(f" \033[91;1mError decoding JSON: {e}\033[0m")
                        print(f" \033[91;1mFull message content: {message}\033[0m")

        except websockets.exceptions.ConnectionClosedOK:
            if __printdebug__: print(f" \033[91;1mClient {websocket.remote_address} disconnected\033[0m")
            self.connected_clients.remove(websocket)

    def save_file(self, file_path, file_content):
        try:
            with open(file_path, "w") as file:
                file.write(file_content)
            if __printdebug__: print(f" \033[91;1mSFDL upload successfully: {file_path}\033[0m")
            add_weg_gui_log(f"SFDL upload successfully: {file_path}")
        except Exception as e:
            if __printdebug__: print(f" \033[91;1mError saving file {file_path}: {e}\033[0m")
            add_weg_gui_log(f"Error saving file {file_path}: {e}")

    async def stop_download(self):
        global __ftp_aborted__
        __ftp_aborted__ = True
        add_weg_gui_log(f'Stopping all downloads ...')
        if __printdebug__: print(f" \033[91;1mStopping all downloads ... (Web-GUI Command)\033[0m")
        await FTPDownloader.close_all_ftp_connections(__ftp_loader__)
        await FileWatcher.stop_watching(__file_watcher__)
        __file_watcher_thread__.join()
        
    async def start_download(self):
        global __ftp_aborted__
        __ftp_aborted__ = False
        add_weg_gui_log(f'Starting download!')
        if __printdebug__: print(f" \033[91;1mStarting download ... (Web-GUI Command)\033[0m")
        watchdog_thread = threading.Thread(target=start_watchdog, args=(monitor, password, destination, 2))
        watchdog_thread.daemon = True
        watchdog_thread.start()

    async def send_message_to_all_clients(self, message):
        for client in self.connected_clients:
            await client.send(message)

    def start_server(self):
        start_server = websockets.serve(self.handle_client, self.ip, self.port)
        asyncio.get_event_loop().run_until_complete(start_server)
        print(f" \033[93;1mStarted WebSocket-Server at\033[0m \033[93;1mws://\033[0m\033[92;1m{self.ip}\033[93;1m:\033[0m\033[92;1m{self.port}\033[0m")

class SaugerWebserver:
    def __init__(self, base64_encoded_zip, host='127.0.0.1', port=8869, ws_port=8769, debug=False):
        self.app = Flask(__name__)
        self.base64_encoded_zip = base64_encoded_zip
        self.host = host
        self.port = port
        self.ws_port = ws_port
        self.debug = debug
        
        # set 404 page
        self.app.register_error_handler(404, self.page_not_found)

        @self.app.route('/')
        def home():
            return render_template_string(self.read_file_from_zip('index.html'), host=host, ws_port=self.ws_port, version=__version__)
        
        @self.app.route('/<filename>')
        def load_file(filename):
            return render_template_string(self.read_file_from_zip(filename))

    def read_file_from_zip(self, file):
        try:
            zip_data = base64.b64decode(self.base64_encoded_zip)
            with ZipFile(BytesIO(zip_data), 'r') as zip_file:
                return zip_file.read(file).decode('utf-8')
        except Exception as e:
            self.page_not_found(e)

    def page_not_found(self, e):
        return render_template_string(self.read_file_from_zip('404.html'), error=e)
    
    def run(self):
        try:
            # os.environ['FLASK_ENV'] = 'production'
            # os.environ['WERKZEUG_RUN_MAIN'] = 'true'
            log = logging.getLogger('werkzeug')
            log.setLevel(logging.ERROR)
            self.app.run(host=self.host, port=self.port, debug=self.debug, use_reloader=False)
            print(f" \033[93;1mStarted Webserver at\033[0m \033[93;1mhttp://\033[0m\033[92;1m{self.host}\033[93;1m:\033[0m\033[92;1m{self.port}\033[0m")
        except Exception as e:
            print(f" \033[91;1mError running the web server: {e}\033[0m")

class web_gui_updater:
    def __init__(self, websocket_server):
        self.websocket_server = websocket_server

    async def send_updates(self):
        try:
            while True:
                message1 = json.dumps(__web_gui_logs__)
                await self.websocket_server.send_message_to_all_clients(message1)
                message2 = json.dumps(__web_gui_updates__)
                await self.websocket_server.send_message_to_all_clients(message2)
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            pass

def start_watchdog(monitor, password, destination, threads):
    if monitor is not None:
        __monitor_mode__ = True
        watchdog_path = os.path.normpath(monitor)
        if os.path.exists(watchdog_path) and os.path.isdir(watchdog_path):
            # watcher = FileWatcher(watchdog_path, password, destination, threads)
            # watcher.start_watching()
            __file_watcher__ = FileWatcher(watchdog_path, password, destination, threads)
            __file_watcher__.start_watching()
        else:
            print(f" \033[91;1mError: Sorry, but {watchdog_path} does not exist!\033[0m")
            print("\033[1;97m")  # white bold text
            parser.print_help()
            print("\033[0m")  # default text
            sys.exit(1)
            
def start_websocket_server(ws_host, ws_port, destination):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    ws_server = WebSocketServer(ip=ws_host, port=ws_port, upload_directory=destination)
    web_gui_updates = web_gui_updater(ws_server)
    ws_server.start_server()
    try:
        asyncio.ensure_future(web_gui_updates.send_updates())
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.stop()
        loop.run_until_complete(loop.shutdown_asyncgens())
        asyncio.set_event_loop(None)
        
def start_webserver(www_host, www_port, ws_port):
    try:
        www_server = SaugerWebserver(base64_encoded_zip=__web_data__, host=www_host, port=www_port, ws_port=ws_port, debug=__printdebug__)
        www_server.run()
    except Exception as e:
        print(f" \033[91;1mError starting webserver: {e}\033[0m")

def bytes2human(byte_size, base=1000):
    if byte_size == 0:
        return "0 B"
    size_names = ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]
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
        print(f" \033[91;1mSFDL read error: {e}\033[0m")
        if __use_web_gui__: add_weg_gui_log(f'SFDL read error: {e}')
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
    if __use_web_gui__: add_weg_gui_log(f'Open SFDL file: {filename}')
    
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
            if __use_web_gui__: add_weg_gui_log(f'Error downloading SFDL file: {e}')
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
            if __use_web_gui__: add_weg_gui_log('SFDL Error: Enter URL or local file only!')

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

def create_web_gui_file_array(release_name, files):
    global __web_gui_updates__
    __web_gui_updates__ = []
    data_array = [release_name, 0, 0, 0, []]
    totalSize = 0
    for file in files:
        totalSize += file[1]
        data_array[4].append([os.path.basename(file[0]), file[1], 0, 0])
    data_array[1] = totalSize
    __web_gui_updates__.append(data_array)

def add_weg_gui_log(log):
    global __web_gui_logs__
    __web_gui_logs__.append(log)

# connect to ftp server and create a file index
def get_ftp_file_index(ftp_host, ftp_port, ftp_user, ftp_pass, ftp_path, proxy, release_name):
    print(f" \033[93;1mGet FTP-Index for:\033[0m \033[95;1m{release_name}\033[0m")
    if __use_web_gui__: add_weg_gui_log(f'Get FTP-Index for: {release_name}')
    try:
        ftp_client = FTPList(ftp_host, ftp_port, ftp_user, ftp_pass, ftp_path, proxy)
        ftp_client.ftp_login()
        files = ftp_client.list_files()
        return files
    except (error_temp, error_perm, error_proto, error_reply, Error, socket_error) as e:
        print(f" \033[91;1mFTP-List Error: {e}\033[0m")
        if __use_web_gui__: add_weg_gui_log(f'FTP-List Error:  {e}')
    finally:
        if ftp_client:
            ftp_client.close()

# connect to ftp server and download files for index
def download_files(ftp_host, ftp_port, ftp_user, ftp_pass, destination, max_threads, release_name, files, proxy, sfdl_file):
    global __ftp_loader__
    
    print(f" \033[93;1mStart Download:\033[0m \033[95;1m{release_name}\033[0m")
    if __use_web_gui__: add_weg_gui_log(f'Start Download: {release_name}')
    total_size = bytes2human(sum(file_size for _, file_size in files), base=1000)
    print(f" \033[93;1mLoading\033[0m \033[92;1m{len(files)}\033[0m \033[93;1mfiles\033[0m \033[92;1m({total_size})\033[0m \033[93;1musing\033[0m \033[92;1m{max_threads}\033[0m \033[93;1mthreads\033[0m")
    if __use_web_gui__: add_weg_gui_log(f'Loading {len(files)} files ({total_size}) using {max_threads} threads')
    try:
        # ftp_downloader = FTPDownloader(ftp_host, ftp_port, ftp_user, ftp_pass, destination, max_threads, release_name, proxy, sfdl_file)
        # ftp_downloader.connect()
        # ftp_downloader.download_multiple_files(files)
        __ftp_loader__ = FTPDownloader(ftp_host, ftp_port, ftp_user, ftp_pass, destination, max_threads, release_name, proxy, sfdl_file)
        __ftp_loader__.connect()
        __ftp_loader__.download_multiple_files(files)
    except (error_temp, error_perm, error_proto, error_reply, Error, socket_error) as e:
        print(f" \033[91;1mFTP-Download Error: {e}\033[0m")
        if __use_web_gui__: add_weg_gui_log(f'FTP-Download Error: {e}')

def main(ftp_host, ftp_port, ftp_user, ftp_pass, ftp_path, destination, max_threads, release_name, proxy, sfdl_file): 
    files = None
    files = get_ftp_file_index(ftp_host, ftp_port, ftp_user, ftp_pass, ftp_path, proxy, release_name)
    
    # create data array for web-gui updates
    if __use_web_gui__:
        create_web_gui_file_array(release_name, files)
        if __printdebug__: print(f'__web_gui_updates__: {__web_gui_updates__}')
    
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
                if __use_web_gui__: add_weg_gui_log(f'Error: Download size {bytes2human(total_bytes, base=1000)}, free space {bytes2human(disc_free_space_bytes, base=1000)}')
                if __use_web_gui__: add_weg_gui_log(f'Error: Not enough free space at {destination}!')
            else:
                download_files(ftp_host, ftp_port, ftp_user, ftp_pass, destination, max_threads, release_name, files, proxy, sfdl_file)
        else:
            print(f" \033[91;1mError: Unable to create new downloads in {destination} (write protection)\033[0m")
            if __use_web_gui__: add_weg_gui_log(f'Error: Unable to create new downloads in {destination} (write protection)')
    else:
        print(" \033[91;1mError: No files to download! (Empty files index)\033[0m")
        if __use_web_gui__: add_weg_gui_log('Error: No files to download! (Empty files index)')

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
    if __use_web_gui__: add_weg_gui_log(f'pySFDLSauger {__version__} (GrafSauger)')

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
    parser.add_argument("--gui", help="Enable Web-GUI WS+HTTP Server (default: None)")
    parser.add_argument("--www_host", help="Webserver HOST/IP (default: 127.0.0.1)")
    parser.add_argument("--www_port", help="Webserver Port (default: 8869)")
    parser.add_argument("--ws_host", help="WebSocket HOST/IP (default: 127.0.0.1)")
    parser.add_argument("--ws_port", help="WebSocket Port (default: 8769)")
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
    
    # files to exclude from download
    exclude_list = None if args.exclude is not None else '.scr, .vbs'
    __exclude_files__ = [name.strip().lower() for name in exclude_list.split(",")]
    
    www_gui = args.gui if args.gui is not None else None
    
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

    if is_destination_valid(destination) == False:
        print(f" \033[91;1mError: Unable to access or write to {destination}\033[0m")
        print("\033[1;97m") # white bold text
        parser.print_help()
        print("\033[0m") # default text
        sys.exit(1)

    # set socks5 proxy
    proxy = None
    if proxy_host is not None and proxy_port is not None:
        proxy = Proxy(proxy_host, proxy_port, username=proxy_user, password=proxy_pass)
    
    # set default password for encrypted sfdl files
    if password is None:
        password = "mlcboard.com"
    
    # start web gui
    if www_gui is not None:
        __use_web_gui__ = True
        
        www_host = None if args.www_host is not None else '127.0.0.1'
        www_port = None if args.www_port is not None else 8869
        ws_host = None if args.ws_host is not None else '127.0.0.1'
        ws_port = None if args.ws_port is not None else 8769
        
        websocket_thread = threading.Thread(target=start_websocket_server, args=(ws_host, ws_port, destination))
        websocket_thread.daemon = True
        websocket_thread.start()
        
        time.sleep(0.1)
        
        weserver_thread = threading.Thread(target=start_webserver, args=(www_host, www_port, ws_port))
        weserver_thread.daemon = True
        weserver_thread.start()
        
        time.sleep(3)
        
        # add monitor service
        if monitor is None:
            monitor = destination
        __file_watcher_thread__ = threading.Thread(target=start_watchdog, args=(monitor, password, destination, threads))
        __file_watcher_thread__.daemon = True
        __file_watcher_thread__.start()
        
        while True:
            time.sleep(1)

    # start watchdog service to monitor path for new sfdl files
    if monitor is not None:
        watchdog_thread = threading.Thread(target=start_watchdog, args=(monitor, password, destination, threads))
        watchdog_thread.daemon = True
        watchdog_thread.start()
        
        while True:
            time.sleep(1)

    if sfdl is None:
        print(" \033[91;1mError: No SFDL file set!\033[0m")
        print("\033[1;97m") # white bold text
        parser.print_help()
        print("\033[0m") # default text
        sys.exit(1)
        
    if sfdl is not None:
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

    if www_gui is None:
        if all(variable is not None for variable in [ftp_host, ftp_port, ftp_path]):
            main(ftp_host, int(ftp_port), ftp_user, ftp_pass, ftp_path, destination, int(threads), release_name, proxy, sfdl)
        else:
            print(f" \033[91;1mError: Missing FTP data from SFDL file!\033[0m")
            print("\033[1;97m") # white bold text
            parser.print_help()
            print("\033[0m") # default text
            sys.exit(1)