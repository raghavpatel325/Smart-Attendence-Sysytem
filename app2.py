from flask import Flask, render_template, Response, jsonify, request
import cv2
import face_recognition
import numpy as np
import os
from datetime import datetime
import csv
from flask import send_file
app = Flask(__name__)

known_face_encodings = []
known_face_names = []

def load_and_encode_images(image_folder):
    for filename in os.listdir(image_folder):
        if filename.endswith(".jpg") or filename.endswith(".png"):
            image_path = os.path.join(image_folder, filename)
            image = face_recognition.load_image_file(image_path)
            encodings = face_recognition.face_encodings(image)
            if encodings:
                known_face_encodings.append(encodings[0])
                known_face_names.append(os.path.splitext(filename)[0])

image_folder = "photos"
load_and_encode_images(image_folder)

students = known_face_names.copy()
face_locations = []
face_encodings = []
face_names = []
s = True

current_date = datetime.now().strftime("%Y-%m-%d")
csv_filename = current_date + '.csv'

def write_to_csv(name, current_time):
    with open(csv_filename, 'a', newline='') as f:
        lnwriter = csv.writer(f)
        lnwriter.writerow([name, current_time])

video_capture = None

@app.route('/start_camera')
def start_camera():
    global video_capture
    if video_capture is None or not video_capture.isOpened():
        video_capture = cv2.VideoCapture(0)
        if video_capture.isOpened():
            return jsonify(success=True)
        else:
            return jsonify(success=False)
    return jsonify(success=True)

@app.route('/stop_camera')
def stop_camera():
    global video_capture
    if video_capture is not None and video_capture.isOpened():
        video_capture.release()
    return jsonify(success=True)

def gen_frames():
    global video_capture
    while True:
        if video_capture is None or not video_capture.isOpened():
            break
        success, frame = video_capture.read()
        if not success:
            break
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = small_frame[:, :, ::-1]
        if s:
            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
            face_names = []
            for face_encoding in face_encodings:
                matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
                name = ""
                face_distance = face_recognition.face_distance(known_face_encodings, face_encoding)
                best_match_index = np.argmin(face_distance)
                if matches[best_match_index]:
                    name = known_face_names[best_match_index]

                face_names.append(name)
                if name in known_face_names:
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    bottomLeftCornerOfText = (10, 100)
                    fontScale = 1.5
                    fontColor = (255, 0, 0)
                    thickness = 2
                    lineType = cv2.LINE_AA

                    shadow_color = (0, 0, 0)
                    text = name.upper() + ' PRESENT'
                    cv2.putText(frame, text, (bottomLeftCornerOfText[0] + 2, bottomLeftCornerOfText[1] + 2), font, fontScale, shadow_color, thickness + 2, lineType)
                    cv2.putText(frame, text, bottomLeftCornerOfText, font, fontScale, fontColor, thickness, lineType)

                    if name in students:
                        students.remove(name)
                        current_time = datetime.now().strftime("%H:%M:%S")
                        write_to_csv(name, current_time)
                elif name == "":
                    name = ""
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    bottomLeftCornerOfText = (10, 100)
                    fontScale = 1.5
                    fontColor = (0, 0, 255)
                    thickness = 2
                    lineType = cv2.LINE_AA

                    shadow_color = (0, 0, 0)
                    text = name.upper()
                    cv2.putText(frame, text, (bottomLeftCornerOfText[0] + 2, bottomLeftCornerOfText[1] + 2), font, fontScale, shadow_color, thickness + 2, lineType)
                    cv2.putText(frame, text, bottomLeftCornerOfText, font, fontScale, fontColor, thickness, lineType)

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
@app.route('/capture_picture_feed')
def capture_picture_feed():
    capture_picture_folder = "capture_pictures"
    capture_picture_filename = os.listdir(capture_picture_folder)[-1]
    return send_file(os.path.join(capture_picture_folder, capture_picture_filename), mimetype='image/jpeg')
@app.route('/capture_picture')
def capture_picture():
    global video_capture
    if video_capture is not None and video_capture.isOpened():
        success, frame = video_capture.read()
        if success:
            capture_picture_folder = "capture_pictures"
            if not os.path.exists(capture_picture_folder):
                os.makedirs(capture_picture_folder)

            capture_picture_filename = f"capture_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.jpg"
            cv2.imwrite(os.path.join(capture_picture_folder, capture_picture_filename), frame)
            return send_file(os.path.join(capture_picture_folder, capture_picture_filename), mimetype='image/jpeg')
        else:
            return jsonify(success=False)
    else:
        return jsonify(success=False)
def gen_frames_new_user():
    global video_capture
    while True:
        if video_capture is None or not video_capture.isOpened():
            break
        success, frame = video_capture.read()
        if not success:
            break
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed_new_user')
def video_feed_new_user():
    return Response(gen_frames_new_user(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/save_picture', methods=['POST'])
def save_picture():
    data = request.get_json()
    name = data['name']
    global video_capture
    if video_capture is not None and video_capture.isOpened():
        success, frame = video_capture.read()
        if success:
            save_picture_folder = "photos"
            if not os.path.exists(save_picture_folder):
                os.makedirs(save_picture_folder)

            save_picture_filename = f"{name}.jpg"
            cv2.imwrite(os.path.join(save_picture_folder, save_picture_filename), frame)
            load_and_encode_images(image_folder)
            stop_camera()
            return jsonify(success=True)
        else:
            return jsonify(success=False)
    else:
        return jsonify(success=False)

@app.route('/')
def index():
    return render_template('index1.html')

if __name__ == '__main__':
    app.run(debug=True)