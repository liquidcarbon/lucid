# lucid/gcp.py

__doc__ = """
Modules for interacting with Google Cloud Platform.

Prerequisites:
!pip3 install --upgrade google-auth-oauthlib google-cloud-bigquery \
    google-api-python-client pyarrow
restart notebook
"""

#-----------------------------------------------------------------------------
# Logging
#-----------------------------------------------------------------------------
import logging
_l = logging.getLogger(__name__)


#-----------------------------------------------------------------------------
# Imports & Options
#-----------------------------------------------------------------------------

# External imports
from google_auth_oauthlib import flow
from googleapiclient.discovery import build
import pandas as pd
import requests

# Internal imports


#-----------------------------------------------------------------------------
# Auth
#-----------------------------------------------------------------------------

def auth(client_secrets='client_secrets.json', scopes=[
    "https://www.googleapis.com/auth/bigquery",
    "https://www.googleapis.com/auth/drive.readonly",
]):
    """Authorization for Google services.

    Requires ``client_secrets.json`` nearby.
    """
    appflow = flow.InstalledAppFlow.from_client_secrets_file(
        client_secrets, scopes=scopes
    )

    try:
        appflow.run_console()
        _l.info('Success!')
        return appflow.credentials
    except Exception as e:
        _l.error(f'Failed to authenticate: {e}')
        return


#-----------------------------------------------------------------------------
# Drive
#-----------------------------------------------------------------------------

def ls(link, credentials) -> pd.DataFrame:
    """Lists files in a folder."""

    check_credentials(credentials)
    service = build('drive', 'v3', credentials=credentials)

    fields = '''(
        name, mimeType, size,
        createdTime, modifiedTime,
        lastModifyingUser(emailAddress), id
    )'''.replace('\n','')
    folder_id = api_folder_id(link)

    results = service.files().list(
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
        q=f"'{folder_id}' in parents and trashed = false",
        fields = f"nextPageToken, files{fields}"
    ).execute()
    gfiles = pd.DataFrame(results.get('files', []))
    gfiles['size'] = gfiles['size'].fillna('0').astype(int)
    return gfiles


def get(link, credentials, stream=True) -> requests.models.Response:
    """Executes HTTP GET to Google Drive API to fetch the filestream."""

    check_credentials(credentials)

    r = requests.get(
        api_file_url(link),
        headers={"Authorization": f"Bearer {credentials.token}"},
        stream=stream
    )

    try:
        r.raise_for_status()
        _l.debug('stream initialized')
    except requests.HTTPError as e:
        _l.error(e)

    return r


#-----------------------------------------------------------------------------
# Utility Functions
#-----------------------------------------------------------------------------

def api_file_url(url_or_id: str) -> str:
    """Converts the Google Drive file ID or "Get link" URL to an API URL.

    from https://drive.google.com/file/d/<ID>/view?usp=sharing
      to https://www.googleapis.com/drive/v3/files/<ID>?alt=media
    """

    if '/' in url_or_id:
        gid = url_or_id.split('/')[-2]
    else:
        gid = url_or_id

    return f"https://www.googleapis.com/drive/v3/files/{gid}?alt=media"


def api_folder_id(url_or_id: str) -> str:
    """Converts the Google Drive folder ID or "Get link" URL to an API ID.

    from https://drive.google.com/drive/folders/<ID>?usp=sharing
      to <ID>
    """

    if '/' in url_or_id:
        return url_or_id.split('/')[-1].split('?')[0]
    else:
        return url_or_id


def check_credentials(credentials) -> None:
    """Checks that credentials contain a token."""

    if not hasattr(credentials, 'token'):
        _l.fatal('invalid credentials')
        raise AttributeError("token not found in credentials")
    return
