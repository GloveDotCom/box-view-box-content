from flask import Flask, jsonify, redirect
import requests
import time
import settings as s
import json


app = Flask(__name__)


@app.route('/')
def hello():
    """A simple route they will return a JSON structure of files in your root box directory

    Args:
        None

    """
    try:
        root_folder_files = get_folder_files()                                          # gets root folder files/items
    except Exception as ex:
        return 'There was a problem using the Box Content API: {}'.format(ex.message), 500

    return jsonify(root_folder_files)


@app.route('/view/<file_id>')
def view(file_id):
    """ Uses Content API and View API to generate a URL for the file_id provided

    Args:
        file_id: Box's unique string identifying a file.
    """

    try:
        boxcloud_link = get_boxcloud_for_file(file_id)                    # obtains the URL for the file from box folder
    except Exception as ex:
        return 'There was a problem using the Box Content API: {}'.format(ex.message), 500

    # build Box's authorization header
    headers = {
        'Authorization': 'Token {}'.format(s.VIEW_API_KEY),
        'Content-Type': 'application/json',
    }

    documents_resource = '/documents'
    url = s.VIEW_API_URL + documents_resource
    data = json.dumps({'url': boxcloud_link})                   # stores the URL for a POST (upload) request to view api
    api_response = requests.post(url, headers=headers, data=data)
    document_id = api_response.json()['id']         # obtains the id for the document that was uploaded to the view api

    for i in range(30):                                                 # for loop to give the files 30 secs to process
        document_resource = '{}/{}'.format(documents_resource, document_id)             # build the resource with doc id
        url = s.VIEW_API_URL + document_resource
        api_response = requests.get(url, headers=headers)

        status = api_response.json()['status']
        if status == 'done':
            break
        elif status == 'error':
            break
        else:
            time.sleep(1)

    if status != 'done':
        return 'There was a problem generating a preview for this document! \
                The error message provide by the api is "{}"'.format(api_response.json()['error_message']), 500

    sessions_resource = '/sessions'                                          # To view a document first create a session
    url = s.VIEW_API_URL + sessions_resource
    data = json.dumps({'document_id': document_id})                                   # adds doc id for the POST request

    api_response = requests.post(url, headers=headers, data=data)                       # POST request with the doc id
    session_id = api_response.json()['id']                                                          # obtains session id

    view_url = '{}/{}/view?theme=dark'.format(s.SESSIONS_URL, session_id)          # builds URL with session id w/ theme

    return redirect(view_url)


def get_folder_items(folder_id=0):
    """ A function that returns a list of items in the folder_id provided

    Args:
        folder_id: A valid folder's ID - default value is 0

    """
    folders_resource = '/folders/{}/items'.format(folder_id)                                        # build the resource
    url = s.CONTENT_API_URL + folders_resource                                                    # build the API's URL
    auth = {'Authorization': 'Bearer {}'.format(s.CONTENT_ACCESS_TOKEN)}              # build Box's authorization header

    api_response = requests.get(url, headers=auth)
    api_response.raise_for_status()

    return api_response.json()


def get_folder_files(folder_id=0):
    """A function that will return a folder and its items

    Args:
        folder_id: A valid folder's ID - default value is 0

    """
    folder_items = get_folder_items(folder_id)                                           # obtain items in the folder_id

    folder_files = [
        item for item in folder_items['entries'] if item['type'] == 'file'      # loop to obtain only items of type file
    ]

    folder_items['entries'] = folder_files                                              # store files in this sub array
    folder_items['total_count'] = len(folder_files)                                     # store length in this sub array

    return folder_items


def get_boxcloud_for_file(file_id):
    """Function that retrieves the location (URL) of the file via the response's header

    Args:
        file_id: Box's unique string identifying a file.
    """

    files_resource = '/files/{}/content'.format(file_id)                                         # builds the resource
    url = s.CONTENT_API_URL + files_resource                                       # build the final URL with API's path
    auth = {'Authorization': 'Bearer {}'.format(s.CONTENT_ACCESS_TOKEN)}

    api_response = requests.get(url, headers=auth, allow_redirects=False)
    api_response.raise_for_status()

    boxcloud_link = api_response.headers['Location']            # the response header is where the location URL is found

    return boxcloud_link


if __name__ == '__main__':
    app.debug = True
    app.run()
