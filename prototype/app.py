import time

import flask
from flask import Flask, Response, request, render_template, redirect, url_for, jsonify
import requests
from flask_pymongo import PyMongo
import flask_login
import hashlib
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy
# import urllib.parse

from instance.config import marvel_apiKey_public, marvel_apiKey_private, gif_apiKey, spotify_client_id_apiKey, spotify_client_secret_apiKey, spotify_bearer_token

app = Flask(__name__, instance_relative_config=True)

CLIENT_ID = spotify_client_id_apiKey
CLIENT_SECRET = spotify_client_secret_apiKey
SPOTIPY_CLIENT_ID = spotify_client_id_apiKey
SPOTIPY_CLIENT_SECRET = spotify_client_secret_apiKey

app.config["MONGO_URI"] = "mongodb://localhost:27017/mcuftw"
mongo = PyMongo(app)

sp = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET))

# Helper functions
def get_Marvelpayload():  # return hashed keys as payload for calling Marvel API
    ts = str(round(time.time()))
    str2hash = ts + marvel_apiKey_private + marvel_apiKey_public
    apikey = hashlib.md5(str2hash.encode())
    payload = {'ts': ts, 'apikey': marvel_apiKey_public, 'hash': apikey.hexdigest()}
    return payload


def get_seriesIMG(url):
    payload = get_Marvelpayload()
    response = requests.get(url, params=payload)
    res = response.json()
    result = res['data']['results'][0]
    print("This is keys in result", result.keys())
    series_img = result['thumbnail']['path'] + '.' + result['thumbnail']['extension']
    return series_img

def get_memeIMG(char_name):
    url = 'https://api.giphy.com/v1/gifs/search?api_key=' + gif_apiKey + '&q=' + str(
        char_name) + '&lang=en&rating=pg-13&limit=3'
    response = requests.request("GET", url)
    res = response.json()
    gifs = []
    for gif in res['data']:
        gif_info = [
            gif['embed_url'],
            gif['url']
        ]
        gifs.append(gif_info)
    return gifs

def get_character(name):  # calls Marvel API to get background image, description, comics_url, and wiki_url
    payload = get_Marvelpayload()
    payload['name'] = name
    response = requests.get("https://gateway.marvel.com:443/v1/public/characters", params=payload)
    print("This is requests.url:", response.url)
    res = response.json()
    print("This is response", response.json())
    if res['data']['count'] == 0:
        # message = "Sorry, the character you are searching has no results. Please try using other names."
        return None
    else:
        message = 'Here is the result for \'' + name.upper() + '\' '
        result = res['data']['results'][0]
        print("This is keys in result", result.keys())
        description = result['description']
        char_img = result['thumbnail']['path'] + '.' + result['thumbnail']['extension']
        series_url = result['series']['items'][0]['resourceURI']
        series_img = get_seriesIMG(series_url)
        comics_url = list(filter(lambda d: d['type'] == "comiclink", result['urls']))[0]['url']
        wiki_url = list(filter(lambda d: d['type'] == "wiki", result['urls']))[0]['url']
        memes = get_memeIMG(name)
        songs = get_songs(name)
        # print("This is comics_url", comics_url)
        data = {
            'message': message,
            'description': description,
            'char_img': char_img,
            'comics_url': comics_url,
            'wiki_url': wiki_url,
            'series_img': series_img,
            'memes': memes,
            'songs': songs
        }
        return data

def get_songs(char_name):
    db = mongo.db.songs
    songs = []
    all_songs = db.find({'character_name': char_name})
    for song in all_songs:
        songs.append({
            'song_name': song['name'],
            'song_artist': song['artist'],
            'spotify_url': song['spotify_url']
        })
    return songs
    
def search_songs(name,song):
    url = "https://api.spotify.com/v1/search?q=" + song + "&type=track&market=US&limit=1"
    headers = { 'Authorization': 'Bearer ' + spotify_bearer_token }
    response = requests.request("GET", url, headers=headers)
    res = response.json()
    song_url = res['tracks']['items']['external_urls']['spotify']
    song_name = res['tracks']['items']['name']
    song_artist = res['tracks']['items']['artists']['name']
    # add the single song to the db 
    db = mongo.db.songs
    db.insert({
        'character_name': name,
        'song_name': song_name,
        'song_artist': song_artist,
        'spotify_url': song_url
        })
    return
    

@app.route('/', methods=['GET', 'POST'])
def home():  # put application's code here
    if request.method == 'GET':
        return render_template('index.html')

@app.route('/test', methods=['GET'])
def test():  # put application's code here
    return render_template('test.html')


@app.route('/search', methods=['GET', 'POST'])
def search():  # put application's code here
    if request.method == 'GET':
        return render_template('search.html')
    if request.method == 'POST':
        # print("This is request.form:", request.form.keys())
        name = request.form.get("name")
        song = request.form.get("song")
        # name = urllib.parse.quote(name)
        # print("This is the name you're searching:", name)
        # print("This is url encoded name:", urllib.parse.quote(name))
        char_data = get_character(name)
        search_songs(name,song)
        # character_songs = get_songs(song)
        return render_template('search.html', char_data=char_data)


@app.route('/credits', methods=['GET'])
def credit():
    return render_template('credits.html')


if __name__ == '__main__':
    app.run()
