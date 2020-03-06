from __future__ import print_function

import base64
import logging
import os
import os.path
import pickle
import pprint
import time

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from emailMsg import Attachment, Email, EmailMsg

logger = logging.getLogger("attachBack")

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
API_NAME = 'gmail'
API_VER = 'v1'


def authenticate(tokenFileName: str, credFileName: str):
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(tokenFileName):
        with open(tokenFileName, 'rb') as token:
            creds = pickle.load(token)
            logger.info("Credentials read from %s", tokenFileName)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Credentials were expired, attempting to refresh.")
            creds.refresh(Request())
        else:
            logger.info(
                "Credentials could not be found, asking for authorization from the user.")
            flow = InstalledAppFlow.from_client_secrets_file(
                credFileName, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(tokenFileName, 'wb') as token:
            pickle.dump(creds, token)
            logger.info("Credentials saved to %s for future use.",
                        tokenFileName)
    logging.info("Successfully authenticated to gmail.")
    return creds


def downloadAttachmentsFromGmail(service, downloadPath: str, query: str = '', contentType: str = ''):
    emails = Email(service, query=query)

    for email in emails:
        for attachment in email:
            if contentType in attachment.contentType:
                logger.debug("Mimetype of attachment: %s",
                             attachment.contentType)
                # TODO: actually want to give the file a fake name and extension from the mimetype
                if attachment.filename:
                    # TODO: just proving a point, not a good way to do this, for now skipping
                    #  it seems some filenames may be files with parameters like in HTTP
                    #  so, should try to fix the filenames to be on what is allowable by the OS. Example:
                    # Content-Type: image/png; name="sys_attachment.do?sys_id=f2b51517db5f1700abe8a5f74b961956"
                    # Content-Transfer-Encoding: base64
                    # Content-Disposition: inline; filename="sys_attachment.do?sys_id=f2b51517db5f1700abe8a5f74b961956"
                    # Content-ID: <sys_attachment.dosys_idf2b51517db5f1700abe8a5f74b961956@SNC.84ec9c02de157ddb>
                    if '?' not in attachment.filename:
                        # TODO: deal with invalid path names
                        logger.debug("Filename: %s", attachment.filename)
                        if downloadPath[-1] == '/' or downloadPath[-1] == '\\':
                            seperator = ''
                        else:
                            seperator = '/'
                        path = ''.join(
                            [downloadPath, seperator, attachment.filename])
                        # TODO: deal with duplicate names
                        f = open(path, 'wb')
                        f.write(attachment.bytes)
                        f.close()


def main():
    load_dotenv()
    logLevel = os.getenv('ATTACH_LOG_LEVEL', 'INFO')
    downloadPath = os.getenv('ATTACH_DOWNLOAD_PATH', './')
    appCredentials = os.getenv('ATTACH_APP_CREDENTIALS', './credentials.json')
    apiToken = os.getenv('ATTACH_API_TOKEN', './token.pickle')
    query = os.getenv('ATTACH_GMAIL_SEARCH', '')
    contentType = os.getenv('ATTACH_CONTENT_TYPE', '')

    LOGFORMAT = "%(asctime)s %(levelname)s - %(name)s.%(funcName)s - %(message)s"
    logging.basicConfig(level=logLevel, format=LOGFORMAT)
    logging.getLogger('googleapiclient').setLevel(logging.WARNING)

    creds = authenticate(apiToken, appCredentials)

    service = build(API_NAME, API_VER, credentials=creds,
                    cache_discovery=False)

    downloadAttachmentsFromGmail(service, downloadPath, query, contentType)


if __name__ == '__main__':
    main()

# TODO: make parameters globally available, and commandline param settable
# TODO: content-type filtering more flexible (perhaps regex, or list of types)
# TODO: comment
# TODO: document how to set up and create credentials
# TODO: store messageids that have been downloaded to prevent re-downloading on future runs.
