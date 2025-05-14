from functools import partial
import subprocess
from pytubefix import YouTube,Search
import threading
import os
from time import sleep

threads = []

import sys
print_lock = threading.Lock()
progressbars = False
downloadinfo = {}
messages = {}


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
	bar_length = 50
	filled_length = int(bar_length * bytes_downloaded // total_size)
	bar = "█" * filled_length + "-" * (bar_length - filled_length)
	message = f"{downloadinfo[index]}: |{bar}| {percentage_of_completion:5.1f}%"
	messages[index] = message
	if progressbars:
		with print_lock:
			sys.stdout.write(f"\033[{index + 1};0H")  # move to line index+1
			sys.stdout.write(message)
			sys.stdout.flush()

def download_url(url:str,index:int):
	global progressbars
	yt_video = YouTube(url,on_progress_callback=partial(progress_callback,index=index))
	downloadinfo[index] = f"{yt_video.title} video".ljust(50)
	yt_audio = YouTube(url,on_progress_callback=partial(progress_callback,index=index+1))
	downloadinfo[index+1] = f"{yt_audio.title} audio".ljust(50)
	downloadinfo[index+2] = F"{yt_audio.title} merging".ljust(50)
	message = f"{downloadinfo[index+2]}: not started"
	messages[index+2] = message
	if progressbars:
		with print_lock:
			sys.stdout.write(f"\033[{index + 3};0H")  # move to line index+1
			sys.stdout.write(message)
			sys.stdout.flush()
	video_stream = yt_video.streams.filter(progressive=False, file_extension='mp4',only_video=True).first()
	audio_stream = yt_audio.streams.filter(progressive=False, file_extension='mp4',only_audio=True).first()
	video_thread = threading.Thread(target=video_stream.download,kwargs={"output_path": "downloads/videos/","filename": f"{sanitize_filename(yt_video.title)}.mp4"})
	video_thread.start()
	threads.append(video_thread)
	audiothread = threading.Thread(target=audio_stream.download,kwargs={"output_path": "downloads/audios/","filename": f"{sanitize_filename(yt_audio.title)}.m4a"})
	audiothread.start()
	threads.append(audiothread)
	merge_thread = threading.Thread(target=merge_videos,args=(video_thread,audiothread,yt_video.title,index+2))
	merge_thread.start()
	threads.append(merge_thread)
def merge_videos(video_thread,audiothread,title,index:int):
	global progressbars
	video_thread.join()
	audiothread.join()
	message = f"{downloadinfo[index]}: started"
	messages[index] = message
	if progressbars:
		with print_lock:
			sys.stdout.write(f"\033[{index + 1};0H")  # move to line index+1
			sys.stdout.write(message)
			sys.stdout.flush()
	video_path = os.path.join("downloads","videos", F"{sanitize_filename(title)}.mp4")
	audio_path = os.path.join("downloads","audios", F"{sanitize_filename(title)}.m4a")
	output_path = os.path.join("videos", F"{sanitize_filename(title)}.mp4")
	merge_command = [
		"ffmpeg",
		"-i", video_path,
		"-i", audio_path,
		"-c:v", "copy",
		"-c:a", "aac",
		"-strict", "experimental",
		output_path
	]
	subprocess.run(merge_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
	os.remove(video_path)
	os.remove(audio_path)
	message = f"{downloadinfo[index]}: completed"
	messages[index] = message
	if progressbars:
		with print_lock:
			sys.stdout.write(f"\033[{index + 1};0H")  # move to line index+1
			sys.stdout.write(message)
			sys.stdout.flush()

def waitfordownloadsandexit():
	global progressbars
	print("\033[2J", end="")  # Clear screen
	print("\033[H", end="")
	for _ in messages:
		print(messages[_])
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