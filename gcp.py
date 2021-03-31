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
from google.auth.transport.requests import Request
from google.cloud import bigquery
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import numpy as np
import pandas as pd
import requests

# Internal imports

#-----------------------------------------------------------------------------
# Auth
#-----------------------------------------------------------------------------

class GoogleAuth:
    """Handles Google OAuth.

    Methods and Attributes
    ----------------------
    credentials: google.oauth2.credentials.Credentials
        the Google Credentials object
    credentials.expiry: datetime.datetime
        when credentials expire (1 hr from the time of authentication)
    refresh_token()
        refresh token never expires, and you can use it
        to exchange it for an access token as needed
    connect_bq(project_id)
        connect to a BigQuery project
    """

    def __init__(self, client_secrets='client_secrets.json', scopes=[
        "https://www.googleapis.com/auth/bigquery",
        "https://www.googleapis.com/auth/drive.readonly",
    ]):
        """
        Parameters
        ----------
        client_secrets: str
            path to client_secrets file that identifies this application
            default is 'client_secrets.json'
        scopes: List[str]
            https://developers.google.com/identity/protocols/oauth2/scopes
            defaults are Drive(read only) and BigQuery
        """
        self.flow = flow.InstalledAppFlow.from_client_secrets_file(
            client_secrets, scopes=scopes
        )

        try:
            self.flow.run_local_server(port=8765)
            # self.flow.run_console()
            _l.info('auth successful')
            self.credentials = self.flow.credentials
        except Exception as e:
            _l.error(f'Failed to authenticate: {e}')
            self.credentials = None

    def refresh_token(self):
        if self.credentials.expired:
            self.credentials.refresh(Request())
            _l.debug('token refreshed')

    def connect_bq(self, project_id):
        try:
            bqc = bigquery.Client(
                project=project_id,
                credentials=self.credentials
            )
            _l.info('connected to BigQuery')
            return bqc
        except Exception as e:
            _l.error(e)
            raise(e)
            return None

    def _check_credentials(self):
        if type(self.credentials) != Credentials:
            _l.fatal('invalid credentials')
            raise TypeError('invalid credentials, please rerun GoogleAuth()')
        else:
            self.refresh_token()


#-----------------------------------------------------------------------------
# BQ
#-----------------------------------------------------------------------------

def create_dataset(bqclient, project, dataset_id):
    """Creates a dataset WITHOUT overwriting dataset tables if they exist."""

    bqclient.create_dataset(
        bigquery.Dataset(f'{project}.{dataset_id}'),
        exists_ok = True
    )
    _l.info(f'dataset {dataset_id} created')
    return


def create_table(bqclient, table_id, schema, drop=True):
    """Creates a table (optionally drops if exists)"""

    if drop:
        try:
            bqclient.delete_table(table_id)
            _l.info(f'table {table_id} dropped')
        except:
            _l.debug(f'table {table_id} not found')

    bqclient.create_table(bigquery.Table(table_id, schema=schema))
    _l.info(f'table {table_id} created')
    return


def drop_table(bqclient, table_id):
    """Drops a table."""

    try:
        bqclient.delete_table(table_id)
        _l.info(f'table {table_id} dropped')
    except:
        _l.error(f'table {table_id} not found')
    return


def lgbqt(bqclient, project, dataset_id):
    """List Google Big Query Tables.  I had to run with it."""
    tables = list(bqclient.list_tables('.'.join([project, dataset_id])))
    df = pd.DataFrame(data={
        'table_id': [t.table_id for t in tables],
        'created': [pd.Timestamp(t.created) for t in tables],
    })
    return df


def rbq(bqclient, q):
    """Runs a simple BQ query."""

    try:
        df = bqclient.query(q).to_dataframe(create_bqstorage_client=False)
        _l.info('BQ response: {0[0]} rows x {0[1]} cols'.format(df.shape))
        return df
    except Exception as e:
        _l.error(e)
        return None


def wbq(bqclient, df, table_id, schema=None):
    """Write dataframe to BQ.

    In simple cases, schema can be inferred from the data.
    It is advisable to define a schema by default."""

    if schema:
        _table_id = bigquery.Table(table_id, schema=schema)
    else:
        _table_id = table_id

    try:
        bqclient.load_table_from_dataframe(df, table_id)
        _l.info(f'wrote {len(df)} rows to {table_id}')
        return
    except Exception as e:
        _l.error(e)
        return


#-----------------------------------------------------------------------------
# Drive
#-----------------------------------------------------------------------------

def gget(link, gauth: GoogleAuth) -> requests.models.Response:
    """Executes HTTP GET to Google Drive API to fetch the filestream."""

    gauth._check_credentials()
    credentials = gauth.credentials

    file_id = api_file_url(link)
    r = requests.get(
        file_id,
        headers={"Authorization": f"Bearer {credentials.token}"},
        stream=True
    )

    try:
        r.raise_for_status()
        _l.debug(f'streaming from {link}')
    except requests.HTTPError as e:
        _l.error(e)

    return r


def ls(link_or_folderid, gauth: GoogleAuth) -> pd.DataFrame:
    """Lists files in a folder."""

    gauth._check_credentials()
    credentials = gauth.credentials

    service = build('drive', 'v3', credentials=credentials,
                    cache_discovery=False)

    fields = '''(
        name, mimeType, size,
        createdTime, modifiedTime,
        lastModifyingUser(emailAddress), id
    )'''.replace('\n','')
    folder_id = api_folder_id(link_or_folderid)

    try:
        results = service.files().list(
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            q=f"'{folder_id}' in parents and trashed = false",
            fields = f"nextPageToken, files{fields}"
        ).execute()
        gfiles = pd.DataFrame(results.get('files', []))
        if 'size' in gfiles.columns:
            gfiles['size(MB)'] = \
            gfiles['size'].fillna('0').astype(np.int64) / 1e6
        else:
            gfiles['size(MB)'] = 0
        return gfiles.iloc[:, [1,0,7,2,3,4,5]]
    except Exception as e:
        _l.error(e)
        return None


#-----------------------------------------------------------------------------
# Utility Functions
#-----------------------------------------------------------------------------

def api_file_url(url_or_id):
    """Converts the Google Drive file ID or "Get link" URL to an API URL.

    from https://drive.google.com/file/d/<ID>/view?usp=sharing
      to https://www.googleapis.com/drive/v3/files/<ID>?alt=media
    """

    if '/' in url_or_id:
        gid = url_or_id.split('/')[-2]
    else:
        gid = url_or_id

    return f"https://www.googleapis.com/drive/v3/files/{gid}?alt=media"


def api_folder_id(url_or_id):
    """Converts the Google Drive folder ID or "Get link" URL to an API ID.

    from https://drive.google.com/drive/folders/<ID>?usp=sharing
      to <ID>
    """

    if '/' in url_or_id:
        return url_or_id.split('/')[-1].split('?')[0]
    else:
        return url_or_id
