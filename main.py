from functools import partial
import subprocess
from pytubefix import YouTube,Search
import threading
import os
from time import sleep
import re
import sys

threads = []

import sys
print_lock = threading.Lock()
progressbars = False
downloadinfo = {}
messages = {}
maxlength = 0

def showmessage(title,index,percentage_of_completion):
	global progressbars, maxlength
	if len(title) > maxlength:
		maxlength = len(title)
	bar_length = 50
	filled_length = int(bar_length * percentage_of_completion/100)
	bar = "█" * filled_length + "-" * (bar_length - filled_length)
	message = f"{title.ljust(maxlength)}: |{bar}| {percentage_of_completion:5.1f}%"
	messages[index] = message
	if progressbars:
		displaymessage(message,index)

def displaymessage(message,index):
	with print_lock:
		sys.stdout.write(f"\033[{index + 1};0H")  # move to line index+1
		sys.stdout.write('\r' + message)
		sys.stdout.flush()

def sanitize_filename(filename):
	# List of characters that are invalid in Windows filenames
	invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']

	for char in invalid_chars:
		filename = filename.replace(char, "")  # Replace invalid characters with "_"

	return filename

def progress_callback(stream, chunk, bytes_remaining,index):
	global progressbars
	total_size = stream.filesize
	bytes_downloaded = total_size - bytes_remaining
	percentage_of_completion = bytes_downloaded / total_size * 100

	# Print progress bar

	showmessage(downloadinfo[index],index,percentage_of_completion)

def download_url(url:str,index:int):
	global progressbars
	yt_video = YouTube(url,on_progress_callback=partial(progress_callback,index=index))
	downloadinfo[index] = f"{yt_video.title} video"
	yt_audio = YouTube(url,on_progress_callback=partial(progress_callback,index=index+1))
	downloadinfo[index+1] = f"{yt_audio.title} audio"
	downloadinfo[index+2] = F"{yt_audio.title} merging"
	showmessage(downloadinfo[index+2],index+2,0)
	video_stream = yt_video.streams.filter(progressive=False, file_extension='mp4',only_video=True).first()
	audio_stream = yt_audio.streams.filter(progressive=False, file_extension='mp4',only_audio=True).first()
	video_thread = threading.Thread(target=video_stream.download,kwargs={"output_path": "downloads/videos/","filename": f"{sanitize_filename(yt_video.title)}.mp4"})
	video_thread.start()
	threads.append(video_thread)
	audiothread = threading.Thread(target=audio_stream.download,kwargs={"output_path": "downloads/audios/","filename": f"{sanitize_filename(yt_audio.title)}.m4a"})
	audiothread.start()
	threads.append(audiothread)
	merge_thread = threading.Thread(target=merge_videos,args=(video_thread,audiothread,yt_video.title,index+2,yt_video.length,))
	merge_thread.start()
	threads.append(merge_thread)
def merge_videos(video_thread,audiothread,title,index:int,video_length):
	global progressbars
	video_thread.join()
	audiothread.join()
	message = f"{downloadinfo[index]}: started"
	messages[index] = message
	video_path = os.path.join("downloads","videos", F"{sanitize_filename(title)}.mp4")
	audio_path = os.path.join("downloads","audios", F"{sanitize_filename(title)}.m4a")
	output_path = os.path.join("videos", F"{sanitize_filename(title)}.mp4")
	run_ffmpeg_with_progress(video_path,audio_path,output_path,title,video_length,index)
	os.remove(video_path)
	os.remove(audio_path)

def run_ffmpeg_with_progress(video_path, audio_path, output_path, title, total_duration,index):
	merge_command = [
		"ffmpeg",
		"-y",
		"-i", video_path,
		"-i", audio_path,
		"-c:v", "copy",
		"-c:a", "aac",
		output_path
	]
	if not os.path.exists("ffmpeg merge logs"):
		os.mkdir("ffmpeg merge logs")
	with open(F"ffmpeg merge logs/{sanitize_filename(title)}.log", "w", encoding="utf-8") as logfile:
		process = subprocess.Popen(
			merge_command,
			stderr=subprocess.PIPE,
			stdout=subprocess.DEVNULL,
			universal_newlines=True,
			bufsize=1
		)

		duration_regex = re.compile(r'time=(\d+):(\d+):(\d+)\.(\d+)')

		while True:
			line = process.stderr.readline()
			if not line:
				break
			logfile.write(line)

			match = duration_regex.search(line)
			if match:
				hours, minutes, seconds, millis = map(int, match.groups())
				current_time = hours * 3600 + minutes * 60 + seconds + millis / 100
				progress = min(current_time / total_duration, 1.0)
				showmessage(F"{title} merging",index,progress*100)

		process.wait()

def waitfordownloadsandexit():
	global progressbars
	print("\033[2J", end="")  # Clear screen
	print("\033[H", end="")
	for _ in messages:
		print("")
	for key in messages.keys():
		displaymessage(messages[key],key)
	progressbars = True
	for download in threads:
		download.join()
	exit(0)

while True:
	query = input("what video do you want to download? (exit to exit) ")
	if query == "exit":
		waitfordownloadsandexit()
	videos = Search(query).videos

	while True:
		if len(videos) > 0:
			video = videos[0]
			print(f'Title: {video.title}')
			print(f'URL: {video.watch_url}')
			print(f'Views: {video.views}')
			print(f'Author: {video.author}')
			print(f'Duration: {video.length} sec')
			print('---')
			reaction = input("do you want to download this video? (y/n/exit) ").lower()
			if reaction == "y" or reaction == "yes":
				download_url(video.watch_url,len(downloadinfo))
				break
			elif reaction == "n" or reaction == "no":
				videos.pop(0)
				continue
			elif reaction == "exit":
				print("exiting")
				waitfordownloadsandexit()
			else:
				print("invalid reaction, exiting")
				waitfordownloadsandexit()
		else:
			print("list of videos has ended, exiting")
			break