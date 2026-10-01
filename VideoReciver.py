import cv2

ESP32_STREAM_URL = "http://192.168.4.1:81/stream"

cap = cv2.VideoCapture(ESP32_STREAM_URL)

if not cap.isOpened():
    print("no ESP32-CAM")
    exit()

print("yes ESP32-CAM")

while True:
    ret, frame = cap.read()

    if not ret:
        break

    cv2.imshow("ESP32-CAM Stream", frame)

   
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()