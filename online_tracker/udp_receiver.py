import socket
import cv2

def udp_opencv():
    cap = cv2.VideoCapture('udp://192.168.1.13:5001', cv2.CAP_FFMPEG)
    if not cap.isOpened():
        print('VideoCapture not opened')
        exit(-1)

    while True:
        ret, frame = cap.read()

        if not ret:
            print('frame empty')
            break
        hough_img = track_ball_hough(frame, show=True)
        cv2.imshow('image', hough_img)

        if cv2.waitKey(1)&0XFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


def convert_to_grayscale(img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return gray


def track_ball_hough(image, show=False, save=False, store_name='image.png'):
        img = cv2.medianBlur(convert_to_grayscale(image), 5)
        cimg = image
        circles = cv2.HoughCircles(img ,cv2.HOUGH_GRADIENT,1,20,param1=50,param2=30,minRadius=10,maxRadius=30)
        if not circles is None:
            for i in circles[0,:]:
                # draw the outer circle
                cv2.circle(cimg,(i[0],i[1]),i[2],(0,255,0),2)
                # draw the center of the circle
                cv2.circle(cimg,(i[0],i[1]),2,(0,0,255),3)
        return cimg


def main():
    udp_opencv()


def udp_raw():
    sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    address = ("192.168.1.13", 5001)
    sock.bind(address)
    while True:
        data, addr = sock.recvfrom(1024)
        print(addr)



if __name__ == '__main__':
    main()