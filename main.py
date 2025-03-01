import json
import os
import sys
import asyncio
import time
from datetime import datetime

import cv2
import numpy as np
import aiohttp
from PyQt6.QtCore import QCoreApplication, QRectF, QSize, Qt
from PyQt6.QtGui import (
    QColor,
    QFont,
    QIcon,
    QImage,
    QPainter,
    QPainterPath,
    QPixmap,
    QTextCharFormat,
    QTextCursor,
)
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from pyzbar import pyzbar

scriptDir = os.path.dirname(os.path.abspath(__file__))
os.chdir(scriptDir)

def darken_rgb(RGBColor, amount=1.1):
    darkened = [int(float(value) / float(amount)) for value in RGBColor]
    return f'rgb({darkened[0]}, {darkened[1]}, {darkened[2]})'

brandHexColors = {'bg': '#1A1C1E', 'grey': '#383B40', 'red': '#FF3939', 'blue': '559BFF', 'darkBG': '#0D0E0F'}
brandRGBColors = {'bg': [26, 28, 30], 'grey': [56, 59, 64], 'red': [255, 57, 57], 'white': [255,255,255], 'darkBG': [13, 14, 15]} 
field_ids = {'auto_amp': 1, 'auto_speaker': 2, 'tele_amp': 3, 'tele_speaker': 4, 'trap': 5, 'spotlight': 6, 'harmony': 7, 'parked_position': 8}

r_file, r_size, roboto_font = "Assets/Roboto-Regular.ttf", 13, QFont()
roboto_font.setFamily(r_file.split("/")[-1].split(".")[0])
roboto_font.setPointSize(r_size)

c_file, c_size, cantarell_font = "Assets/Cantarell-Regular.ttf", 16, QFont()
cantarell_font.setFamily(c_file.split("/")[-1].split(".")[0])
cantarell_font.setPointSize(c_size)

with open(f'{scriptDir}/config.json') as f:
    config = json.load(f)

host, apiAuthToken, eventId = config['host'], config['token'], config['event']
previous_server, previous_api_token, prevoiusEventId = host, apiAuthToken, eventId

headers = {
  'Accept': 'application/json',
  'X-Requested-With': 'XMLHttpRequest',
  'Authorization': f'Bearer {apiAuthToken}'
}

batch, uploaded_json_data, uploaded_qr_codes = [], [], []

APP_NAME = '1671 QR Code Scanner'

app = QApplication(sys.argv)
app.setApplicationName(APP_NAME)
app.setDesktopFileName(APP_NAME)
app.setWindowIcon(QIcon(f'{scriptDir}/Assets/1671-icon.png'))
app.setFont(roboto_font)

camera_map = {}

layout, HLayout, combined_widget = QVBoxLayout(), QHBoxLayout(), QWidget()
combined_layout = QVBoxLayout(combined_widget)

central_widget = QWidget()
central_widget.setLayout(layout)

settings_button = QPushButton()
settings_icon = QIcon("Assets/system.png")
settings_button.setIcon(settings_icon)
settings_button.setIconSize(settings_icon.actualSize(QSize(30, 30)))
settings_button.clicked.connect(lambda: window.overlay.show())
settings_button.setStyleSheet("""
    QPushButton { background-color: """ + brandHexColors['grey'] + """; color: white; font-family: Roboto, Arial, sans-serif; border-radius: 8px; min-width: 50px; max-width: 50px; height: 50px; outline: none;} QPushButton:pressed {background-color: """ + brandHexColors['darkBG'] + """;} QPushButton:hover {background-color: """ + darken_rgb(brandRGBColors["grey"]) + """}""")
layout.addWidget(settings_button)

label, image = QLabel(), QImage("Assets/logo.png")
pixmap = QPixmap.fromImage(image)
pixmap = pixmap.scaled(
    pixmap.width() // 5,
    pixmap.height() // 5,
    Qt.AspectRatioMode.KeepAspectRatio,
    Qt.TransformationMode.SmoothTransformation,
)
label.setPixmap(pixmap)
label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
layout.addWidget(label)

matchLabel = QLabel("")
matchLabel.setAlignment(Qt.AlignmentFlag.AlignLeft)
matchLabel.setStyleSheet(f"color: white; background-color: {brandHexColors['darkBG']}; border-radius: 10px;")
HLayout.addWidget(matchLabel)

invis = QLabel("Nothing to see here...")
invis.setStyleSheet(f"color: {brandHexColors['bg']}")

failed_upload, failed_uploads = "", []

data, show_fps, decoded_objects, decode = None, False, None, True

capture, batch_index = True, 0

last_upload_time = time.time()

class terminal:
    global terminal_widget
    error = [
        ("[ ", QColor("white")),
        ("ERROR", QColor("red")),
        (" ] - ", QColor("white")),
    ]
    warning = [
        ("[ ", QColor("white")),
        ("WARNING", QColor("yellow")),
        (" ] - ", QColor("white")),
    ]
    success = [
        ("[ ", QColor("white")),
        ("SUCCESS", QColor("green")),
        (" ] - ", QColor("white")),
    ]
    config = [
        ("[ ", QColor("white")),
        ("Config", QColor("orange")),
        (" ] - ", QColor("white")),
    ]
    Set = [("[ ", QColor("white")), ("SET", QColor("cyan")), (" ] - ", QColor("white"))]

    def print(message, status=None, show_time=False, string=True):
        global terminal_widget
        app.processEvents()

        current_time = datetime.now().strftime("%I:%M:%S %p").lstrip("0")

        if show_time:
            print(f"{current_time} - {message}")
        else:
            print(message)
        if string:
            cursor = terminal_widget.textCursor()
            char_format = QTextCharFormat()
            try:
                if status != terminal.Set and status != None:
                    cursor.movePosition(QTextCursor.MoveOperation.End)
                    if show_time:
                        cursor.insertText(f"{current_time} ", char_format)
                if status and status[0]:
                    cursor.movePosition(QTextCursor.MoveOperation.End)
                    for text, color in status:
                        char_format = QTextCharFormat()
                        char_format.setForeground(color)
                        cursor.insertText(text, char_format)
                    cursor.insertText(message, char_format)
                    cursor.insertText("\n", char_format)
                    cursor.movePosition(QTextCursor.MoveOperation.End)
                    terminal_widget.setTextCursor(cursor)
                elif status == None:
                    cursor.movePosition(QTextCursor.MoveOperation.End)
                    cursor.insertText(message, char_format)
                    cursor.insertText("\n", char_format)
                    cursor.movePosition(QTextCursor.MoveOperation.End)
                    terminal_widget.setTextCursor(cursor)
            except Exception as e:
                print(e)
        else:
            for line in message.splitlines():
                terminal.print(line, status=None, show_time=False)


class SettingsWindow(QWidget):
    global apiAuthToken, host, previous_server, previous_api_token, eventId, prevoiusEventId
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Settings")
        self.setWindowIcon(QIcon(f'{scriptDir}/Assets/1671-icon.png'))
        self.setStyleSheet(f"background-color: {brandHexColors['bg']}")
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        self.setFixedSize(400, 600)

        input_field_style = ("""
        QLineEdit {
            background-color: """ + brandHexColors['grey'] + """;
            color: gray;
            font-family: Roboto, Arial, sans-serif;
            font-size: 15px;
            font-weight: 400;
            border-radius: 8px;
            max-height: 30px;
            min-height: 25px;
        }

        QLineEdit:focus {
            color: white;
        }
        """)

        label_style = ("""
        QLabel {
            color: white;
        }
        """)

        # Create the labels and text fields
        event_input_label = QLabel("Event ID:")
        event_input_label.setStyleSheet(label_style)
        event_input_field = QLineEdit()
        event_input_field.setText(str(eventId))
        event_input_field.setStyleSheet(input_field_style)

        server_input_label = QLabel("Server:")
        server_input_label.setStyleSheet(label_style)
        server_input_field = QLineEdit()
        server_input_field.setText(str(host))
        server_input_field.setStyleSheet(input_field_style)

        api_token_label = QLabel("Scout API Authentication Token:")
        api_token_label.setStyleSheet(label_style)
        api_token_field = QLineEdit()
        api_token_field.setText(str(apiAuthToken))
        api_token_field.setStyleSheet(input_field_style)

        apply_button = QPushButton("Apply Changes")
        apply_button.setStyleSheet("""
        QPushButton {
            background-color: """ + brandHexColors['grey'] + """;
            color: white;
            font-family: Roboto, Arial, sans-serif;
            border-radius: 8px;
            min-width: 150px;
            max-width: 155px;
            height: 30px;
            outline: none;

        }

        QPushButton:pressed {
            background-color: """ + brandHexColors['darkBG'] + """;
        }

        QPushButton:hover {
            background-color: """ + darken_rgb(brandRGBColors['red']) + """;
        }
        """)


        settings_layout = QVBoxLayout()
        settings_layout.addWidget(event_input_label)
        settings_layout.addWidget(event_input_field)
        settings_layout.addWidget(server_input_label)
        settings_layout.addWidget(server_input_field)
        settings_layout.addWidget(api_token_label)
        settings_layout.addWidget(api_token_field)
        settings_layout.addWidget(apply_button, alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,)
        self.setLayout(settings_layout)

        previous_server = (server_input_field.text())
        previous_api_token = str(api_token_field.text())
        prevoiusEventId = str(event_input_field.text())

        def apply_changes():
            global apiAuthToken, previous_server, previous_api_token, prevoiusEventId, eventId, host
            if str(api_token_field.text()) != previous_api_token or str(server_input_field.text()) != previous_server or str(event_input_field.text()) != prevoiusEventId:
                if str(api_token_field.text()) != previous_api_token:
                    change_token(api_token_field.text())
                    previous_api_token = str(api_token_field.text())
                if str(server_input_field.text()) != previous_server:
                    change_host(server_input_field.text())
                    previous_server = host
                if str(event_input_field.text()) != prevoiusEventId:
                    change_event(event_input_field.text())
                    prevoiusEventId = event_input_field.text()
        apply_button.clicked.connect(lambda: apply_changes())

class MyMainWindow(QMainWindow):
    global working_cameras
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon(f'{scriptDir}/Assets/1671-icon.png'))
        self.setStyleSheet(f"background-color: {brandHexColors['bg']}")
        self.overlay = SettingsWindow()

    def closeEvent(self, event):
        quit_program()
        event.accept()

    def keyPressEvent(self, event):
        global working_cameras
        if event.key() == Qt.Key.Key_C and not (event.modifiers()):
            if camera.isOpened() and len(working_cameras) > 1:
                select_next_camera()
        if (event.modifiers() & Qt.KeyboardModifier.ControlModifier) and event.key() == Qt.Key.Key_U:
            upload_button.click()
        if (event.modifiers() & Qt.KeyboardModifier.ControlModifier) and (event.modifiers() & Qt.KeyboardModifier.AltModifier) and event.key() == Qt.Key.Key_C:
            clear_terminal()
        if (event.modifiers() & Qt.KeyboardModifier.ControlModifier) and event.key() == Qt.Key.Key_F:
            toggle_show_fps()
        if (event.modifiers() & Qt.KeyboardModifier.ControlModifier) and event.key() == Qt.Key.Key_R:
            if camera.isOpened():
                refresh_cameras()
        if (event.modifiers() & Qt.KeyboardModifier.ControlModifier) and event.key() == Qt.Key.Key_Backspace:
            delete_batch()

class ClickableLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)

    def mousePressEvent(self, event):
        camera_label.setFocus()

class MyLineEdit(QLineEdit):
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return:
            pass
        else:
            super().keyPressEvent(event)
        if (event.modifiers() & Qt.ControlModifier) and (event.modifiers() & Qt.AltModifier) and event.key() == Qt.Key.Key_C:
            clear_terminal()
        if (event.modifiers() & Qt.ControlModifier) and event.key() == Qt.Key.Key_U:
            batch_upload()
        if (event.modifiers() & Qt.ControlModifier) and event.key() == Qt.Key.Key_R:
            if camera.isOpened():
                refresh_cameras()

def toggle_show_fps():
    global show_fps
    show_fps = not show_fps

def findMatch():
    uploadedThisMatch, matchJson, people = 0, [], []

    if len(uploaded_json_data) == 0:
        match = 1
    else:
        match = uploaded_json_data[-1]['game_match_number']
    for item in uploaded_json_data:
        if item['game_match_number'] == match:
            uploadedThisMatch += 1
            matchJson.append(item)

    people = [item['full_name'] for item in matchJson[::-1]]

    if len(people) >= 6:
        clear_terminal()

    people = '\n '.join(set(people))

    if not people:
        return f"{' ' * 22}Match: {match}\n Entries Submitted: {uploadedThisMatch}"
    else:
        return f"{' ' * 22}Match: {match}\n Entries Submitted: {uploadedThisMatch}\nUploaded By\n {people}"

def change_dict_format(data):
    newDict = {}
    scout_data = []
    for x in data:
        if x in field_ids:
            value = data[x]
            if value == 'Didnt':
                value = 'false'
            elif value == 'Did':
                value = 'true'
            scout_data.append({'field_id': field_ids[x], 'value': value})
        else:
            newDict[x] = data[x]
    
    newDict['scout_data'] = scout_data
    return newDict

def dictify(value):
    value = value.replace('", ', '*****NewComma*****')
    value = value.replace('": ', '*****NewColon*****')
    value = value.replace("', ", '*****NewComma*****')
    value = value.replace("': ", '*****NewColon*****')
    
    try:
        value = [i.split('*****NewColon*****') for i in value.strip('{}').replace('"', '').replace("'", '').split('*****NewComma*****')]
        dictValue = {i[0].strip(): i[1].strip() for i in value}
    except:
        dictValue = 'broke'

    return dictValue

def camel_to_snake(camel):
    snake = []
    for letter in camel:
        if letter == letter.upper() and camel.index(letter) != 0:
            snake.append('_')
            snake.append(letter.lower())
        else:
            snake.append(letter.lower())
    return ''.join(snake)

def dict_key_changer(dictionary):
    new = {}
    bad = ['color', 'comments', 'name', 'matchNumber', '']
    for key in dictionary:
        if key not in bad:
            new[camel_to_snake(key)] = dictionary[key]
        elif key == bad[0]:
            new['alliance_color'] = dictionary[key].lower()
        elif key == bad[1]:
            new['other_comments'] = dictionary[key].lower()
        elif key == bad[2]:
            new['full_name'] = dictionary[key].lower()
        elif key == bad[3]:
            new['game_match_number'] = dictionary[key].lower()
        
    return change_dict_format(new)

def update_config(config):
    with open(f'{scriptDir}/config.json', 'w') as f:
        json.dump(config, f)

def formatFile(raw, formatted) -> None:
    dicts, header, body, temp, temp2, comments = [], [], [], [], [], []

    with open(raw, 'r') as rawFile:
        content = rawFile.readlines()
        for line in content:
            scout_str = [x for x in line.split("'scout_data': ")[-1].replace(']}', '}').strip('[]').replace('}, {', '}||{').split('||')]
            scout_list = [i.strip('{}').replace("'", "").split(', ') for i in scout_str]
            scout_dict = {x[0]: x[1] for x in scout_list}

            line = dictify(line)
            line['scout_data'] = scout_dict
            dicts.append(line)
    
    key = [x for x in dicts[0]]
    
    for x in field_ids:
        key.append(x)

    key.pop(key.index('scout_data'))
    key.append(key.pop(key.index('other_comments')))
    spaces = len(max(key, key=len)) + 10

    for x in key:
        header.append(x)
        header.append(' ' * (spaces - len(x)))
    
    for _ in dicts:
        temp.clear()
        temp2.clear()
        comments.clear()
        for x in _:
            if x != 'scout_data' and x != 'other_comments':
                temp.append(_[x])
                temp.append(' ' * (spaces - len(_[x])))
            elif x == 'other_comments':
                comments.append(' ' + _[x])
            elif x == 'scout_data':
                for value in _[x]:
                    value = _[x][value].replace('value:', '').replace('}}', '')
                    temp.append(value)
                    temp.append(' ' * (spaces - len(value)))

        temp.append(''.join(comments))
        temp2.append(''.join(temp))
        body.append(temp2[0].strip().replace('\n', ''))

    with open(formatted, 'w') as formattedFile:
        formattedFile.write(''.join(header)+'\n')
        formattedFile.write('\n'.join(body))

def change_host(host_given):
    global config, host
    if host_given != "":
        if "http" not in str(host_given):
            host_given = str("http://" + host_given)
        config['host'] = str(host_given)
        update_config(config=config)
        host = config['host']
        terminal.print(f'Server is set to: "{host}"', status=terminal.config, show_time=True)

def change_token(token_given):
    global config, apiAuthToken, headers
    if token_given != "":
        config['token'] = str(token_given)
        update_config(config=config)
        apiAuthToken = config['token']
        headers = {
        'Accept': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        'Authorization': f'Bearer {apiAuthToken}'}
        terminal.print(f"API Token Changed.", status=terminal.config, show_time=True)

def change_event(event_given):
    global config, eventId
    if event_given != "":
        config['event'] = str(event_given)
        update_config(config=config)
        eventId = config['event']
        terminal.print(f"Event is set to: {eventId}", status=terminal.config, show_time=True)

def scan_cameras():
    working_cameras = []
    if os.name == "posix":
        try:
            camera_folders = [f for f in os.listdir("/dev") if f.startswith("video")]
            for folder in camera_folders:
                camera_path = os.path.join("/dev", folder)
                scan_camera = cv2.VideoCapture(camera_path)
                if scan_camera.isOpened():
                    working_cameras.append(int(folder[5:]))
                    scan_camera.release()
            return working_cameras
        except Exception as e:
            print(e)
            if len(working_cameras) < 1:
                working_cameras = [0]
    elif os.name == "nt":
        for index in range(0, 2):
            try:
                cap = cv2.VideoCapture(index)
                if cap.isOpened():
                    working_cameras.append(index)
                    cap.release()
            except Exception as e:
                print(e)
            if len(working_cameras) < 1:
                working_cameras = [0]
                return working_cameras
            else:
                return working_cameras
    else:
        working_cameras = [0]
        return working_cameras

def on_camera_selected(index):
    global camera, current_camera
    selected_camera = camera_map[index]
    if selected_camera != current_camera:
        camera.release()
        camera = cv2.VideoCapture(selected_camera)
        current_camera = selected_camera
        print(f"Camera {selected_camera} selected")
        set_camera_proportions()

def select_next_camera():
    if os.name == "posix":
        refresh_cameras()
    if camera_dropdown.count() > 1:
        current_index = camera_dropdown.currentIndex()
        next_index = (current_index + 1) % camera_dropdown.count()
        camera_dropdown.setCurrentIndex(next_index)
        on_camera_selected(next_index)

def refresh_cameras():
    global working_cameras, camera, current_camera, camera_map
    camera.release()
    working_cameras = scan_cameras()
    camera_dropdown.clear()
    camera_map = {}
    gen_cameras()
    current_camera_index = working_cameras.index(current_camera)
    camera_dropdown.setCurrentIndex(current_camera_index)
    camera_map[current_camera_index] = current_camera    
    camera = cv2.VideoCapture(current_camera)
    set_camera_proportions()

def gen_cameras():
    global working_cameras, camera_map
    for index, camera_id in enumerate(working_cameras):
        camera_dropdown.addItem(f"Camera {camera_id}")
        camera_map[index] = camera_id

def change_upload_type(index):
    global upload_as_batch, batch, upload_button
    if upload_type_dropdown.currentText() == "Batch Upload":
        upload_as_batch = True
        retry_button.hide()
        if batch and batch[0]:
            upload_button.show()
        else:
            upload_button.hide()
        terminal.print("Set to scan and upload QR codes as batch.", status=terminal.Set)
    else:
        if failed_upload != "":
            retry_button.show()
        upload_button.hide()
        upload_as_batch = False
        terminal.print("Set to scan and upload QR codes individually.", status=terminal.Set)

async def retry_upload():
    global failed_upload, host, headers, uploaded_json_data
    if failed_upload != "":
        retry_button.hide()
        if host != "":
            if failed_upload not in uploaded_json_data:
                terminal.print("Retrying individual upload...")
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(host, headers=headers, json=failed_upload) as response:
                            if response.status == 201:
                                failed_upload = ""
                                retry_button.hide()
                                terminal.print("Data was sent and received successfully.", status=terminal.success, show_time=True)
                            elif response.status == 422:
                                terminal.print(await response.json()["message"], status=terminal.error, show_time=True)
                                retry_button.show()
                            else:
                                terminal.print("Did not return with expected exit code. Please notify the nearest mentor after trying again.", status=terminal.error, show_time=True)
                                terminal.print("")
                                terminal.print((str(failed_upload) + '\n'))
                                retry_button.show()
                except Exception as e:
                    print(e)
                    terminal.print("Something went wrong when sending the data. Please notify the nearest mentor after trying again.", status=terminal.error, show_time=True)
                    terminal.print("")
                    retry_button.show()
            else:
                terminal.print(f"QR Code has already been uploaded.", status=terminal.error, show_time=True)
        else:
            terminal.print("Server field was left empty. Nowhere to send data.", status=terminal.error, show_time=True)

def delete_batch():
    global batch
    if batch != []:
        batch = []
        upload_button.hide()
        terminal.print("Removed Batch")

def clear_terminal():
    terminal_history.append(str(terminal_widget.toPlainText()))
    terminal_widget.clear()

def quit_program():
    global camera
    camera.release()
    os._exit(0)

async def batch_upload():
    global headers, uploaded_json_data, failed_uploads, batch, host
    upload_button.hide()
    qr_code_number = 0
    if batch != []:
        if len(batch) > 1:
            terminal.print(f"Uploading batch of {len(batch)} QR Codes...", show_time=True)
        elif len(batch) == 1:
            terminal.print(f"Uploading batch of {len(batch)} QR Code...", show_time=True)
        async with aiohttp.ClientSession() as session:
            for item in batch[:]:
                app.processEvents()
                if item not in uploaded_json_data:
                    try:
                        qr_code_number += 1
                        async with session.post(host, headers=headers, json=item) as response:
                            if response.status == 201:
                                uploaded_json_data.append(item)
                                batch.remove(item)
                                terminal.print(f"QR Code: {qr_code_number} - Data was sent and received successfully.", status=terminal.success, show_time=True)
                            elif response.status == 422:
                                terminal.print(f'QR Code: {qr_code_number} - {await response.json()["message"]}', status=terminal.error, show_time=True)
                            else:
                                terminal.print(f"QR Code: {qr_code_number} - Did not return with expected exit code. Please notify the nearest mentor.", status=terminal.error, show_time=True)
                    except Exception as e:
                        print(e)
                        terminal.print(f"QR Code: {qr_code_number} - Something went wrong when sending the data. Please notify the nearest mentor.", status=terminal.error, show_time=True)
                    app.processEvents()
                else:
                    terminal.print(f"QR Code: {qr_code_number} has already been uploaded.", status=terminal.error, show_time=True)
    if batch != []:
        upload_button.show()

def display_frame(pause=False):
    if show_fps:
        start_time = cv2.getTickCount()
    global data, camera, decoded_objects, app, decode
    app.processEvents()
    if not camera.isOpened():
        terminal.print("Camera not detected.", status=terminal.error)
    ret, frame = camera.read()
    frame = cv2.GaussianBlur(frame, (1, 1), 0) # To reduce noise and static
    if not ret:
        True
        # terminal.print("Unable to access camera, It may be opened in another application. ", status=terminal.error)
    if ret:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if decode:
            try:
                decoded_objects = pyzbar.decode(gray)
                if decoded_objects:
                    obj = decoded_objects[0]
                    (x, y, w, h) = obj.rect
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 4)

                    bbox_center_x = x + w / 2
                    bbox_center_y = y + h / 2
                    frame_height, frame_width = frame.shape[:2]
                    frame_center_x = frame_width // 2
                    frame_center_y = frame_height // 2
                    dist = (
                        (bbox_center_x - frame_center_x) ** 2
                        + (bbox_center_y - frame_center_y) ** 2
                    ) ** 0.5

                    max_dist = min(frame_width, frame_height) / 2
                    crosshair_length = int(20 * (1 - dist / max_dist) * 1.1)

                    cv2.line(
                        frame,
                        (frame_center_x - crosshair_length, frame_center_y),
                        (frame_center_x + crosshair_length, frame_center_y),
                        color=(0, 0, 255),
                        thickness=1,
                    )
                    cv2.line(
                        frame,
                        (frame_center_x, frame_center_y - crosshair_length),
                        (frame_center_x, frame_center_y + crosshair_length),
                        color=(0, 0, 255),
                        thickness=1,
                    )
            except Warning as w:
                print(w)
                return
        frame_height, frame_width = frame.shape[:2]
        cv2.line(
            frame,
            (frame_width // 2, frame_height // 2 - 10),
            (frame_width // 2, frame_height // 2 + 10),
            color=(0, 0, 255),
            thickness=1,
        )
        cv2.line(
            frame,
            (frame_width // 2 - 10, frame_height // 2),
            (frame_width // 2 + 10, frame_height // 2),
            color=(0, 0, 255),
            thickness=1,
        )
        flipped_frame = cv2.flip(frame, 1)
        height, width, channel = flipped_frame.shape
        bytes_per_line = 3 * width
        if show_fps:
            # Calculate the frame rate
            end_time = cv2.getTickCount()
            time_elapsed = (end_time - start_time) / cv2.getTickFrequency()
            frame_rate = 1 / time_elapsed
            fps_text = "FPS: {:.2f}".format(frame_rate)

            # Define font, scale, and thickness for text
            text_font = cv2.FONT_HERSHEY_SIMPLEX
            text_scale = 0.65
            text_thickness = 2

            # Calculate text size to determine the mask size
            text_size = cv2.getTextSize(fps_text, text_font, text_scale, text_thickness)[0]
            text_x = 10
            text_y = 30  # Start from a bit lower to fit

            # Create a mask where text will be drawn
            mask = np.zeros_like(flipped_frame)
            cv2.putText(mask, fps_text, (text_x, text_y), text_font, text_scale, (255, 255, 255), text_thickness)

            # Extract the region of interest based on text size
            roi = flipped_frame[text_y - text_size[1] : text_y + 10, text_x : text_x + text_size[0]]

            # Create an inverted version of the ROI
            roi_inverted = cv2.bitwise_not(roi)

            # Adjust the inverted pixels to ensure they avoid neutral tones
            offset = 50
            roi_inverted_adjusted = roi_inverted.astype(np.int16)
            roi_inverted_adjusted = np.where(roi_inverted_adjusted < 128, roi_inverted_adjusted - offset, roi_inverted_adjusted + offset)
            roi_inverted_adjusted = np.clip(roi_inverted_adjusted, 0, 255).astype(np.uint8)

            # Use the mask to combine the original ROI with the inverted and adjusted ROI
            mask_roi = mask[text_y - text_size[1] : text_y + 10, text_x : text_x + text_size[0]]
            final_roi = np.where(mask_roi == 255, roi_inverted_adjusted, roi)

            # Place the final ROI back onto the original frame
            flipped_frame[text_y - text_size[1] : text_y + 10, text_x : text_x + text_size[0]] = final_roi

        qimg = QImage(
            flipped_frame.data,
            width,
            height,
            bytes_per_line,
            QImage.Format.Format_RGB888,
        ).rgbSwapped()
        if pause:
            qimg.fill(QColor(0, 0, 0))
        pixmap = QPixmap.fromImage(qimg)
        rounded_pixmap = QPixmap(pixmap.size())
        rounded_pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(rounded_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True) # Reduce pixilation of the camera frame border
        path = QPainterPath()
        path.addRoundedRect(QRectF(pixmap.rect()), 8, 8)
        painter.setClipPath(path)
        painter.drawPixmap(pixmap.rect(), pixmap)
        painter.end()
        pixmap = pixmap.scaled(
            camera_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        camera_label.setPixmap(rounded_pixmap)
        QCoreApplication.sendPostedEvents()
        app.processEvents()

def set_camera_proportions():
    global camera, camera_label
    camera_label_size = QSize(640, 480)
    camera_label.setFixedSize(camera_label_size)

    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    camera.set(cv2.CAP_PROP_FRAME_WIDTH, camera_label.width())
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_label.height())

    camera_height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
    camera_width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))

window = MyMainWindow()
window.setCentralWidget(central_widget)
window.show()

dropdown_style = ("""
QComboBox {
    font-family: Roboto, Arial, sans-serif;
    outline: none;
    height: 30px;
    background-color: """ + brandHexColors['grey'] + """; 
    color: white; 
    border-radius: 8px;
    border-width:2px; 
    padding-left:10px;
    padding-right:8px;
}
QComboBox::hover {
    background-color: """ + darken_rgb(brandRGBColors['grey']) + """;
}
QAbstractItemView {
    selection-background-color: """+ brandHexColors['blue'] +""";
    font-family: Roboto, Arial, sans-serif;
    font-weight: 400;
    color: white;
    border: none;
    outline: none;
}
QComboBox::down-arrow {
    image: url(Assets/down.png);
    width: 15px;
    padding-right: 10px;
}
QComboBox::drop-down {
    border:none;
}
""")

retry_button = QPushButton("Retry Upload")
retry_button.setStyleSheet("""
QPushButton {
    background-color: """ + brandHexColors["grey"] + """;
    color: white;
    font-family: Roboto, Arial, sans-serif;
    border-bottom-left-radius: 8px;
    border-bottom-right-radius: 8px;
    min-width: 140px;
    max-width: 150px;
    outline: none;

}

QPushButton:pressed {
    background-color: """ + brandHexColors["darkBG"] + """;
}

QPushButton:hover {
    background-color: """ + darken_rgb(brandRGBColors["grey"]) + """;
}
""")

retry_button.clicked.connect(lambda: asyncio.create_task(retry_upload()))
retry_button.hide()

upload_type_dropdown = QComboBox()
upload_type_dropdown.setStyleSheet(dropdown_style)

upload_button = QPushButton("Upload Batch")
upload_button.setStyleSheet("""
QPushButton {
    background-color: """ + brandHexColors["grey"] + """;
    color: white;
    font-family: Roboto, Arial, sans-serif;
    border-bottom-left-radius: 8px;
    border-bottom-right-radius: 8px;
    min-width: 130px;
    max-width: 150px;
    outline: none;

}

QPushButton:pressed {
    background-color: """ + brandHexColors["darkBG"] + """;
}

QPushButton:hover {
    background-color: """ + darken_rgb(brandRGBColors["grey"]) + """;
}
""")

side_buttons_stylesheet = ("""
QPushButton {
    background-color: """ + brandHexColors["grey"] + """;
    color: white;
    font-family: Roboto, Arial, sans-serif;
    font-size: 15px;
    font-weight: 400;
    border-radius: 8px;
    min-width: 100px;
    max-width: 75px;
    min-height: 20px;
    max-height: 25px;
    outline: none;
}

QPushButton:hover {
    background-color: """ + darken_rgb(brandRGBColors["grey"]) + """;
}

QPushButton:pressed {
    background-color: """ + darken_rgb(brandRGBColors["grey"], 1.5) + """;
}
""")

upload_button.clicked.connect(lambda: asyncio.create_task(batch_upload()))

upload_as_batch = False
upload_button.hide()

current_camera_index = 0
camera_dropdown = QComboBox()
camera_dropdown.setStyleSheet(dropdown_style)
camera_dropdown.activated[int].connect(on_camera_selected)

camera_label = ClickableLabel(combined_widget)
camera_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
combined_layout.addWidget(camera_label)
camera_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
camera_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
camera_label.setFocus()
camera_label.setScaledContents(True)

working_cameras = scan_cameras()

gen_cameras()

layout.setSpacing(0)
HLayout.addWidget(camera_label, alignment=Qt.AlignmentFlag.AlignJustify)
HLayout.addWidget(invis)
layout.addLayout(HLayout)

if len(working_cameras) == 0:
    print("Either cameras are not available or they are already being used.")
    os._exit(0)

current_camera = working_cameras[0]
camera = cv2.VideoCapture(current_camera)

set_camera_proportions()

upload_type_dropdown.addItem(f"Individual Upload")
upload_type_dropdown.addItem(f"Batch Upload")

upload_type_dropdown.currentIndexChanged.connect(change_upload_type)

dropdowns_layout = QHBoxLayout()

dropdowns_layout.setSpacing(4)
dropdowns_layout.addStretch(1)
dropdowns_layout.addWidget(
    camera_dropdown,
    alignment=(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop),
)
dropdowns_layout.addWidget(
    upload_type_dropdown,
    alignment=(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop),
)
dropdowns_layout.addStretch(1)

layout.addLayout(dropdowns_layout)

terminal_history = []

terminal_widget = QTextEdit()
terminal_widget.setReadOnly(True)
terminal_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
terminal_widget.setFont(cantarell_font)
terminal_widget.setStyleSheet(f"background-color: {brandHexColors['darkBG']}; color: white; border-radius: 8px; min-width: 900px; max-width: 900px; max-height: 250px; min-height: 200px; font-size: 14px; border: 4px solid {brandHexColors['grey']};")
terminal_widget.hide()

layout.addWidget(
    terminal_widget,
    alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
)
layout.addWidget(
    upload_button, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop
)
layout.addWidget(
    retry_button, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop
)

async def main_loop():
    global capture, camera, decoded_objects, last_upload_time, upload_as_batch, batch, upload_button
    while True:
        app.processEvents()
        while capture:
            matchLabel.setText(findMatch())

            await asyncio.to_thread(display_frame)
            app.processEvents()
            if decoded_objects and ((time.time() - last_upload_time) >= 1.5):
                decode = False
                for obj in decoded_objects:
                    data = obj.data.decode("utf-8")
                    QCoreApplication.sendPostedEvents()
                    last_upload_time = time.time()
                    if len(data.splitlines()) != 0:
                        if data not in uploaded_qr_codes:
                            if (dict_data := dictify(data)) == 'broke':
                                data, decode = {}, True
                                break

                            dict_data['eventId'] = eventId
                            dict_data = dict_key_changer(dict_data)

                            with open(f'{scriptDir}/Raw.txt', 'r') as previous:
                                added = previous.readlines()

                            with open(f'{scriptDir}/Raw.txt', 'a') as previous:
                                if str(dict_data) + '\n' not in added:
                                    previous.write(f'{dict_data}\n')

                            if upload_as_batch:
                                if dict_data not in batch:
                                    if dict_data not in uploaded_json_data:
                                        batch.append(dict_data)
                                        upload_button.setText(f"Upload (x{len(batch)})")
                                        batch_index = batch.index(dict_data)
                                        batch_index += 1
                                        if upload_type_dropdown.currentText() == "Batch Upload":
                                            upload_button.show()
                                        else:
                                            upload_button.hide()
                                        terminal.print(f"QR Code {batch_index} added to batch.")
                                    else:
                                        terminal.print("QR Code has already been uploaded.", status=terminal.error, show_time=True)
                                else:
                                    terminal.print("QR Code has already been added to batch.", status=terminal.error, show_time=True)
                            else:
                                if dict_data not in uploaded_json_data:
                                    try:
                                        app.processEvents()
                                        async with aiohttp.ClientSession() as session:
                                            async with session.post(host, headers=headers, json=dict_data) as response:
                                                if response.status == 201:
                                                    uploaded_json_data.append(dict_data)
                                                    retry_button.hide()
                                                    terminal.print("Data was sent and received successfully.", status=terminal.success, show_time=True)
                                                elif response.status == 422:
                                                    terminal.print(await response.json()["message"], status=terminal.error, show_time=True)
                                                    retry_button.show()
                                                else:
                                                    terminal.print(f'Exit Code:{response.status}')
                                                    terminal.print(f'Context: {await response.text()}')
                                                    terminal.print("Did not return with expected exit code. Please notify the nearest mentor after trying again.", status=terminal.error, show_time=True)
                                                    terminal.print("")
                                                    terminal.print((str(dict_data) + '\n'))
                                                    retry_button.show()
                                    except Exception as e:
                                        print(e)
                                        terminal.print("Something went wrong when sending the data. Please notify the nearest mentor after trying again.", status=terminal.error, show_time=True)
                                        terminal.print("")
                                        terminal.print((str(dict_data) + '\n'))
                                        retry_button.show()
                                else:
                                    terminal.print("QR Code has already been uploaded.", status=terminal.error, show_time=True)
                            dict_data = {}
                        else:
                            terminal.print("QR Code has already been uploaded.", status=terminal.error, show_time=True)
                            dict_data = {}
                data = None
                app.processEvents()
                if not camera.isOpened():
                    camera = cv2.VideoCapture(current_camera)

            formatFile('Raw.txt', 'Formatted.txt')
            app.processEvents()

if __name__ == '__main__':
    asyncio.run(main_loop())
    sys.exit(app.exec())