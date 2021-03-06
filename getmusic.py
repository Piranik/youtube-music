#!/usr/bin/python3
import sys
from lxml import html
import requests
import os
import urllib
import requests
import json
import multiprocessing
import random

programSuffix = ""

def getRecommendations(searchString):
    print("Getting recommendations for %s" % searchString)
    # Process initial search
    data = {}
    dataTuples = getYoutubeRecommendations(getURL(searchString))
    urls, data = processTuples(dataTuples,data)

    # Search all the recommendations for more
    p = multiprocessing.Pool(multiprocessing.cpu_count())
    dataTuples = []
    for datTuple in p.map(getYoutubeRecommendations, urls):
        dataTuples += datTuple
    urls, data = processTuples(dataTuples,data)

    # Add one URL for each artist
    urls = []
    for artist in data:
        song = random.choice(list(data[artist].keys()))
        url = data[artist][song]
        print("Adding %s" % song)
        urls.append(url)

    return urls

def processTuples(dats,data):
    urls = []
    for dat in dats:
        try:
            artist = dat[0].split('-')[0].replace(' ','').lower()
            if artist not in data:
                data[artist] = {}
            if dat[1] < 300000:
                data[artist][dat[0]] = dat[2]
                urls.append(dat[2])
        except:
            pass
    return urls, data
  
def getYoutubeRecommendations(url):
    page = requests.get(url)
    tree = html.fromstring(page.content)
    videos = tree.xpath('//div[@class="watch-sidebar-body"]/ul/li/div')
    urls = []
    for video in videos:
        videoData = video.xpath('./a')
        if len(videoData) == 0:
            continue
        if 'href' not in videoData[0].attrib:
            continue
        nextURL = "https://www.youtube.com" + videoData[0].attrib['href']
        videoData2 = videoData[0].xpath('./span[@class="title"]')
        if len(videoData2) == 0:
            continue
        nextTitle = videoData2[0].text_content().strip()
        if " - " not in nextTitle:
            continue
        videoData2 = videoData[0].xpath('./span[@class="stat view-count"]')
        if len(videoData2) == 0:
            continue
        viewCount = videoData2[0].text_content().strip().replace('views','').replace(',','').replace(' ','')
        views = 0
        try:
            views = int(viewCount)
        except:
            continue
        urls.append((nextTitle,views,nextURL))
        print(nextTitle,views,nextURL)
    return urls


def spotify(user, playlist, oauth):
    url = 'https://api.spotify.com/v1/users/' + \
        user + '/playlists/' + playlist + '/tracks'
    headers = {'Authorization': 'Bearer ' + oauth}
    r = requests.get(url, headers=headers)
    a = r.json()
    trackList = []
    if 'items' not in a:
        print("""
    To get the OAUTH, goto
    https://beta.developer.spotify.com/console/get-playlist-tracks/
    Get an OAUTH token and click "TRY IT". Then copy all the stuff after "Bearer "
""")
        sys.exit(-1)
    for item in a['items']:
        trackList.append(item['track']['artists'][0][
                         'name'] + " - " + item['track']['album']['name'] + " - " + item['track']['name'])
    url = 'https://api.spotify.com/v1/users/' + user + '/playlists/' + playlist
    headers = {'Authorization': 'Bearer ' + oauth}
    r = requests.get(url, headers=headers)
    a = r.json()
    directory = a['name'] + ' - ' + a['id']
    return trackList, directory


def getURL(searchString):
    urlToGet = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(searchString)
    print("Getting %s" % urlToGet)
    page = requests.get(urlToGet)
    tree = html.fromstring(page.content)
    videos = tree.xpath('//h3[@class="yt-lockup-title "]')
    for video in videos:
        videoData = video.xpath('./a[contains(@href, "/watch")]')
        if len(videoData) == 0:
            continue
        if 'title' not in videoData[0].attrib or 'href' not in videoData[0].attrib:
            continue
        title = videoData[0].attrib['title']
        url = "https://www.youtube.com" + videoData[0].attrib['href']
        if 'googleads' in url:
            continue
        print("Found url '%s'" % url)
        try:
            timeText = video.xpath(
                './span[@class="accessible-description"]/text()')[0]
            minutes = int(timeText.split(':')[1].strip())
            if minutes > 12 or timeText.count(":") == 3:
                continue
        except:
            pass
        if 'doubleclick' in title or 'list=' in url or 'album review' in title.lower():
            continue
        print("'%s' = '%s' @ %s " % (searchString, title, url))
        return url
    return ""


def downloadURL(url):
    if len(url) == 0:
        return
    os.system("youtube-dl%s -x --audio-quality 2 --audio-format mp3 %s" %
              (programSuffix, url))

if __name__ == '__main__':
    is_windows = sys.platform.startswith('win')
    if is_windows:
        programSuffix = ".exe"

    trackList = []
    urls = []
    directory = "default"
    if len(sys.argv) > 3:
        trackList, directory = spotify(sys.argv[1], sys.argv[2], sys.argv[3])
    elif len(sys.argv) == 1:
        print("""
To download a single track:

    $ ./getmusic.py "Led Zepplin - Stairway to Heaven"

To download a txt-file playlist:

    $ ./getmusic.py Zepplin.txt

    Make the file, 'Zepplin.txt' that contains a list of artist/track names.
    Songs will be stored in 'Zepplin' folder.


To download a Spotify playlist:

    $ ./getmusic.py USER-ID PLAYLIST-ID OAUTH

    Go into Spotify, find your playlist and copy the USER-ID and PLAYLIST-ID
    To get the OAUTH, goto
    https://developer.spotify.com/web-api/console/get-playlist-tracks/#complete
    Get an OAUTH token and click "TRY IT". Then copy all the stuff after "Bearer "

""")
        sys.exit(1)
    elif '.txt' in sys.argv[1]:
        directory = sys.argv[1].split(".txt")[0]
        with open(sys.argv[1], 'r') as f:
            for line in f:
                trackList.append(line.strip())
    elif len(sys.argv) == 2:
        var = input("Do you want recommendations (y/n)? ")
        if 'y' in var:
            urls = getRecommendations(sys.argv[1])
            directory = sys.argv[1].replace(" ","-")
        else:
            print("Downloading " + sys.argv[1])
            trackList.append(sys.argv[1])
    else:
        print("?")
        sys.exit(1)

    p = multiprocessing.Pool(multiprocessing.cpu_count())
    if len(urls) == 0:
        urls = p.map(getURL, trackList)
        if urls[0] == '':
            print("No songs found.")
            sys.exit(1)
        print("\nTracklist to use:")
        for i in range(len(trackList)):
            print(trackList[i], urls[i])

    try:
        os.mkdir(directory)
    except:
        if directory == "default":
            pass
        else:
            print("Directory '%s' already exists, exiting." % directory)
            sys.exit(-1)
    os.chdir(directory)
    p = multiprocessing.Pool(multiprocessing.cpu_count())
    p.map(downloadURL, urls)
    print("%d songs downloaded to %s." % (len(urls), directory))
