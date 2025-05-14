from pytubefix import Search

results = Search('BANKZITTERS BEZORGEN ZO VER MOGELIJK EEN PIZZA IN 1 DAG')
for video in results.videos:
    print(f'Title: {video.title}')
    print(f'URL: {video.watch_url}')
    print(f'Duration: {video.length} sec')
    print('---')