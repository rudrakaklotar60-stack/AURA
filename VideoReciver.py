import cv2
import threading
import time
from collections import deque



url = {
    "front": "http://192.168.4.2:81/stream",
    "left":  "http://192.168.4.3:81/stream",
    "right": "http://192.168.4.4:81/stream",
    "back":  "http://192.168.4.5:81/stream",
}

bf = 10 #buffering frames

#max -> time diff. btw camaras
diff = 0.100       # 100 ms


class CameraReceiver:

    def __init__(self, name, url):
        self.name = name
        self.url = url

        self.cap = None

        self.running = False
        self.thread = None

        # Each item:
        # (timestamp, frame)
        self.buffer = deque(maxlen=bf)

        self.lock = threading.Lock()

        self.frames_received = 0
        self.last_timestamp = None

    def connect(self):

        

        self.cap = cv2.VideoCapture(self.url)

        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not self.cap.isOpened():

            print(f"[{self.name}] not connect")

            return False


        return True


    def start(self):

        if not self.connect():
            return False

        self.running = True

        self.thread = threading.Thread(
            target=self._capture_loop,
            daemon=True
        )

        self.thread.start()

        return True

   

    def _capture_loop(self):

        while self.running:

            ret, frame = self.cap.read()

            if not ret:

                print(f"[{self.name}] read fail")

                
                self.cap.release()

                time.sleep(1)

                self.connect()

                continue

            timestamp = time.perf_counter()

            with self.lock:

                self.buffer.append(
                    (timestamp, frame)
                )

                self.last_timestamp = timestamp
                self.frames_received += 1

   
    def get_frames(self):


        with self.lock:
            return list(self.buffer)


    def stop(self):

        self.running = False

        if self.thread is not None:
            self.thread.join(timeout=1)

        if self.cap is not None:
            self.cap.release()


#sync
def synchronize_frames(cameras):

    """
    Find one frame from each camera whose timestamps
    are as close together as possible.
    """

    buffers = {}

    
    for name, cam in cameras.items():

        frames = cam.get_frames()

        if len(frames) == 0:
            return None

        buffers[name] = frames

    
    # Find the newest camera frame timestamp

    newest_timestamp = max(
        frames[-1][0]
        for frames in buffers.values()
    )
    
    # Find closest frame to newest timestamp

    synchronized = {}

    timestamps = []

    for name, frames in buffers.items():

        best_frame = min(
            frames,
            key=lambda item: abs(item[0] - newest_timestamp)
        )

        timestamp, frame = best_frame

        synchronized[name] = {
            "timestamp": timestamp,
            "frame": frame
        }

        timestamps.append(timestamp)

    
    # sync error
    

    sync_error = max(timestamps) - min(timestamps)

    if sync_error > diff:

        return None

    return {
        "frames": synchronized,
        "timestamp": sum(timestamps) / len(timestamps),
        "sync_error": sync_error
    }


def create_grid(frames):

    front = frames["front"]["frame"]
    left  = frames["left"]["frame"]
    right = frames["right"]["frame"]
    back  = frames["back"]["frame"]

    
    width = 640
    height = 480

    front = cv2.resize(front, (width, height))
    left  = cv2.resize(left,  (width, height))
    right = cv2.resize(right, (width, height))
    back  = cv2.resize(back,  (width, height))

    
    cv2.putText(front, "front", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    cv2.putText(left, "left", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    cv2.putText(right, "right", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    cv2.putText(back, "back", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    top = cv2.hconcat([front, left])
    bottom = cv2.hconcat([right, back])

    grid = cv2.vconcat([top, bottom])

    return grid


def main():

    cameras = {}

    for name, url in url.items():

        cameras[name] = CameraReceiver(name, url)

    
    for camera in cameras.values():

        camera.start()

    print("\n All camera receivers started")

    #sync loop
    try:

        while True:

            synchronized = synchronize_frames(cameras)

            if synchronized is None:

                time.sleep(0.001)

                continue

            frames = synchronized["frames"]

            sync_error = synchronized["sync_error"]

            timestamp = synchronized["timestamp"]

            #show
            grid = create_grid(frames)

            cv2.putText(grid, f"SYNC: {sync_error * 1000:.1f} ms", (20, grid.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

            cv2.imshow(
                "4-Camera Synchronized View",
                grid
            )

            if cv2.waitKey(1) & 0xFF == ord("q"):

                break

    finally:

        print("\nStopping cameras...")

        for camera in cameras.values():

            camera.stop()

        cv2.destroyAllWindows()

   



if __name__ == "__main__":
    main()