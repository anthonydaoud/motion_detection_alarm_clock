# import the necessary packages
from picamera.array import PiRGBArray
from picamera import PiCamera
import argparse
import datetime
import imutils
import time
import cv2
import pygame

# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("--hour", type =int, required=True,
	help="hour to be woken up")
ap.add_argument("--minute", type=int, required=True,
	help="minute to be woken up")
ap.add_argument("--audio", type=str, required=True,
	help="audio file to be played")
args = vars(ap.parse_args())

"""Set up default variable values, can be edited for specific user preferences.
Specifically, users should edit the min_area based on how far the camera is located
from their bed and the min_motion_frames based on how much motion is required to 
turn off the camera. When editing these values, users should set show_video to
True and then visually see what is recognised as motion for the their setup of
variable values."""
resolution = [608, 400]
fps = 20
min_area = 5000
min_motion_frames = 16
delta_thresh = 5
show_video = False
	
#wait until wake up time
temp = datetime.datetime.now()
wakeUp = temp.replace(hour=args["hour"], minute=args["minute"], second=0)
waitTime = wakeUp - datetime.datetime.now()
waitSeconds = waitTime.total_seconds()
time.sleep(abs(waitSeconds))

#set up audio components
pygame.init()
pygame.mixer.init()
pygame.mixer.music.load(args["audio"])

# initialize the camera and grab a reference to the raw camera capture
camera = PiCamera()
camera.resolution = tuple(resolution)
camera.framerate = fps
rawCapture = PiRGBArray(camera, size=tuple(resolution))
 
# Initialize the previous frame, frame motion counter, and boolean indicating
# if the person is in bed 
prev = None
motionCounter = 0
isInBed = True

# capture frames from the camera
for fr in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
	# grab an array representing the image
	frame = fr.array
	 
	# resize the frame, convert it to grayscale, and blur it
	frame = imutils.resize(frame, width=500)
	grayFrame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
	grayFrame = cv2.GaussianBlur(grayFrame, (21, 21), 0)
 
	# if the previous frame is None, initialize it
	if prev is None:
		prev = grayFrame.copy().astype("float")
		rawCapture.truncate(0)
		continue
 
	# compute the difference between the current frame and previous
	frameDelta = cv2.absdiff(grayFrame, cv2.convertScaleAbs(prev))
	prev = grayFrame.copy().astype("float")

	# threshold the delta image, dilate the thresholded image to fill
	# in holes, then find contours on thresholded image
	threshold = cv2.threshold(frameDelta, delta_thresh, 255,
		cv2.THRESH_BINARY)[1]
	threshold = cv2.dilate(threshold, None, iterations=2)
	cnts = cv2.findContours(threshold.copy(), cv2.RETR_EXTERNAL,
		cv2.CHAIN_APPROX_SIMPLE)
	cnts = cnts if imutils.is_cv2() else cnts[1]
 
	
	#initialize a boolean indicating that the user may have awoken
	mayHaveAwoken = False

	# check all contours detected
	for c in cnts:
		# ignore contours below the minimum size
		if cv2.contourArea(c) < min_area:
			continue
 
		# calculate the bounding box for the contour and draw it on the frame
		(x, y, w, h) = cv2.boundingRect(c)
		cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

		#if there is a contour, then the user may have awoken
		mayHaveAwoken = True
 
	# check if the user may be awake (true if a contour was detected)
	if mayHaveAwoken:

		#increase the number of frames in which motion has occurred
		motionCounter += 1
 
		# check if there are enough frames with consistent motion
		if motionCounter >= min_motion_frames:
			# if it passes the threshold, then the user is awake
			isInBed = False
 
	# otherwise, the reset the motion counter
	else:
		motionCounter = 0

	# play alarm sound if the user is still in bed 
	if isInBed == True:
		pygame.mixer.music.play(0)
	else:
		break

	# check to see if the frames should be displayed to screen.
	# This is included to provide a clearer understanding of what
	# building a bounding box is.
	if show_video:
		cv2.imshow("Alarm Sample", frame)
		key = cv2.waitKey(1) & 0xFF
 
	# clear the stream in preparation for the next frame
	rawCapture.truncate(0)
