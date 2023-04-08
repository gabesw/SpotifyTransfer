from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseNotAllowed
import requests
from SpotifyTransfer import settings
import json
import spotipy
from spotipy.oauth2 import SpotifyOAuth


sp_oauth = SpotifyOAuth(
    client_id=settings.CLIENT_ID,
    client_secret=settings.CLIENT_SECRET,
    redirect_uri=settings.REDIRECT_URI,
    scope=settings.SCOPE
)

def login(request):
    # Redirect the user to the Spotify authorization page
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

def index(request):
    code = request.GET.get('code')
    if code == None: #if no code in url, redirect to login
        return redirect(login)
    context = {"code":code}
    return render(request, "home/index.html", context)

def transfer(request, user_id, code):
    #userId = "w2bt1346cvsygxlmz3nc3xau7" #TODO: MAKE DYNAMIC
    userId = user_id #get userid from url
    url = f'https://api.spotify.com/v1/users/{userId}/playlists'
    Spotifyheaders = {
    'Authorization': f'Bearer {getBearerToken()}',  # DEBUG ONLY
    'limit': '50'
    }
    # Make the GET request
    Spotifyresponse = requests.get(url, headers=Spotifyheaders)

    responseData = {"items": []}
    playlists = list()

    # Check the status code of the response
    if Spotifyresponse.status_code == 200:
        # If the request was successful add playlists to dict
        responseData = Spotifyresponse.json()
        for item in responseData["items"]:
            playlists.append({"name": item["name"]})# create dict entry and add name to dict
            playlists[len(playlists)-1]["id"] = item["id"] #add playlist id to dict to send back to view when selected
            if len(item["images"]) != 0: #if the playlist has an image, add the smallest one to the dict - thats all we need
                playlists[len(playlists)-1]["image_url"] = item["images"][len(item["images"])-1]["url"] #set image field smallest image from image list
            else:
                playlists[len(playlists)-1]["image_url"] = "https://play-lh.googleusercontent.com/CT1M2pKlUhGx4w5UHqarn6oSU_sa7L7XRW2-hQrfNi9oou6W81PbJnWi-9PbEfC_3g=s180" #else set image to blank white box - TODO: put this in static
            #print(playlists[len(playlists)-1]) #print dict for debug
        
    else:
        # If the request was unsuccessful, print an error message
        print(f'Error: {Spotifyresponse.status_code} - {Spotifyresponse.reason}')

    context = {"playlists": playlists, "code": code, "user_id": user_id}
    return render(request, "home/transfer.html", context)

def createPlaylists(request):
    if request.method == 'POST':
        print(request.body) #DEBUG
        body = json.loads(request.body)
        playlist_ids = body.get("playlists")
        user_id = body.get("user_id")
        #print(playlist_ids)
        code = body.get("code")
        token_info = sp_oauth.get_access_token(code)
        access_token = token_info['access_token']

        # Use the access token to create a Spotipy client
        sp = spotipy.Spotify(auth=access_token)

        # Use the Spotipy client to create a playlist on the user's account
        oauth_id = sp.me()['id']

        for id, name in playlist_ids.items():
            url = f'https://api.spotify.com/v1/playlists/{id}/tracks'
            Spotifyheaders = {
            'Authorization': f'Bearer {getBearerToken()}'  # DEBUG ONLY
            }
            # Make the GET request
            Spotifyresponse = requests.get(url, headers=Spotifyheaders)
            responseData = {"items": []}
            tracks = list()
            #TODO: have playlist name and id in dict instead of list of track ids
            if Spotifyresponse.status_code == 200:
                responseData = Spotifyresponse.json()
                for item in responseData["items"]:
                    #tracks.append({"id": item["track"]["id"]}) #add track id to tracks list
                    tracks.append(item["track"]["uri"]) #add track uri not id as thats what i need to make the put request to add the songs to the new playlist
            else:
                # If the request was unsuccessful, print an error message
                print(f'Error: {Spotifyresponse.status_code} - {Spotifyresponse.reason}')
            #create playlist with name and add tracks from list at end of each loop
            print("New Playlist:", name, "\nTracks:") #DEBUG
            print(tracks) #DEBUG
            #uris = ",".join(tracks) #comma separated list of track URIs for PUT request
            new_playlist = sp.user_playlist_create(oauth_id, name) #create playlist in oauth user's account with each name
            sp.playlist_replace_items(playlist_id=new_playlist["id"], items=tracks) #populate the new playlist with tracks


        #TODO: loop though each playlist from json data and create that playlist on the oauth account
        #playlist_name = 'My New Playlist'
        #sp.user_playlist_create(oauth_id, playlist_name)

        return HttpResponse("Success", status=200) #return 200 ok if successful
    return HttpResponseNotAllowed(['POST']) #return 405 method not allowed if get request

def getBearerToken():
    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = f"grant_type=client_credentials&client_id={settings.CLIENT_ID}&client_secret={settings.CLIENT_SECRET}"
    response = requests.post(url, data=data, headers=headers)
    accessToken = ""
    try:
        accessToken = response.json().get("access_token")
    except requests.exceptions.JSONDecodeError:
        print("Failed to get Bearer Token")
    return accessToken