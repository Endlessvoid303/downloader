from pytubefix import YouTube,Search
import threading
from time import sleep

threads = []

def download_url(url:str):
	yt = YouTube(url)
	print(F"downloading video: {yt.title}")
	ys = yt.streams.get_highest_resolution(progressive=False)
	ys.download(output_path="videos/")
	print(F"video downloaded: {yt.title}")

def waitfordownloadsandexit():
	print("waiting for downloads to finish...")
	for download in threads:
		download.join()
	print("all downloads have finished, exiting...")
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
			print(f'Duration: {video.length} sec')
			print('---')
			reaction = input("do you want to download this video? (y/n/exit) ").lower()
			if reaction == "y" or reaction == "yes":
				thread = threading.Thread(target=download_url, args=(video.watch_url,))
				thread.start()
				threads.append(thread)
				sleep(1)
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