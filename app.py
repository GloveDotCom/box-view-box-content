from flask import Flask, jsonify, redirect
import requests
import time
import settings as s
import json


app = Flask(__name__)


@app.route('/')
def hello():
    """A simple route that will return a JSON structure of files in your root box directory

    Args:
        None
    """

    try:
        # gets root folder files/items
        root_folder_files = get_folder_items(folder_id=0) #change to items for navigations
    except Exception as ex:
        return 'There was a problem using the Box Content API: {}'.format(ex.message), 500

    return jsonify(root_folder_files)


@app.route('/view/<file_id>')
def view(file_id):
    """ Uses Content API and View API to generate an URL for the file_id provided

    Args:
        file_id: Box's unique string identifying a file.
    """

    try:
        # obtains an URL for the file from box folder
        boxcloud_link = get_boxcloud_for_file(file_id)
    except Exception as ex:
        return 'There was a problem using the Box Content API: {}'.format(ex.message), 500

    # build Box's authorization header
    headers = {
        'Authorization': 'Token {}'.format(s.VIEW_API_KEY),
        'Content-Type': 'application/json',
    }

    documents_resource = '/documents'
    url = s.VIEW_API_URL + documents_resource
    # stores the URL for a POST (upload) request to VIEW API
    data = json.dumps({'url': boxcloud_link})
    # upload the file to the VIEW API for conversion
    api_response = requests.post(url, headers=headers, data=data)

    document_id = api_response.json()['id']

    # gives the file(s) 30 secs to process/convert
    for i in range(30):
        document_resource = '{}/{}'.format(documents_resource, document_id)
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

    # In order to view the doc without a token one needs a session
    sessions_resource = '/sessions'
    url = s.VIEW_API_URL + sessions_resource
    data = json.dumps({'document_id': document_id})
    api_response = requests.post(url, headers=headers, data=data)
    session_id = api_response.json()['id']

    # builds URL with session id + theme
    view_url = '{}/{}/view?theme=dark'.format(s.SESSIONS_URL, session_id)

    return redirect(view_url)

@app.route('/folder/<folder_id>/<type>')
def folder_view_type(folder_id,type):
    """A function that will return items of a specific type from a folder

    :param folder_id: Box's unique string identifying a folder.
    :param type: A Box object type
    :return: JSON structure containing a list of files
    """

    return jsonify(get_folder_files(folder_id,type=type))

@app.route('/folder/<folder_id>')
def folder_view(folder_id):
    """ A function that will return all files in the specific folder

    :param file_id: Box's unique string identifying a file.
    :return: JSON structure containing a list of files
    """
    return jsonify(get_folder_items(folder_id))


def get_folder_items(folder_id=0):
    """ A function that returns a list of all items found in a folder provided via Content API

    Args:
        folder_id: A valid folder's ID - default value is 0
    """

    folders_resource = '/folders/{}/items'.format(folder_id)
    url = s.CONTENT_API_URL + folders_resource
    auth = {'Authorization': 'Bearer {}'.format(s.CONTENT_ACCESS_TOKEN)}

    api_response = requests.get(url, headers=auth)
    api_response.raise_for_status()

    return api_response.json()

def get_folder_files(folder_id, type='file'):
    """A function that will return items of a specific folder via Content API

    Args:
        folder_id: A valid folder's ID - default value is 0 (root folder)
    """

    folder_items = get_folder_items(folder_id)

    # loop to obtain only items of type file
    folder_files = [
        item for item in folder_items['entries'] if item['type'] == type
    ]
    # store files in the folder_items list

    folder_items['entries'] = folder_files
    folder_items['total_count'] = len(folder_files)

    return folder_items


def get_boxcloud_for_file(file_id):
    """Function that retrieves the location (URL) of the file via the response's header

    Args:
        file_id: Box's unique string identifying a file.
    """

    files_resource = '/files/{}/content'.format(file_id)
    url = s.CONTENT_API_URL + files_resource
    auth = {'Authorization': 'Bearer {}'.format(s.CONTENT_ACCESS_TOKEN)}

    api_response = requests.get(url, headers=auth, allow_redirects=False)
    api_response.raise_for_status()
    # the response header is where the location URL is found
    boxcloud_link = api_response.headers['Location']

    return boxcloud_link


if __name__ == '__main__':
    app.debug = True
    app.run()
