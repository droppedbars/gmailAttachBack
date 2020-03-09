from __future__ import print_function

import base64
import json
import logging
import mimetypes
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

RECORD_FILENAME = 'records.txt'


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


def downloadAttachmentsFromGmail(service, downloadPath: str, recordFile: str, records: list, query: str = '', contentType: str = ''):
    emails = Email(service, query=query)

    for email in emails:
        logger.debug("Email ID: %s", email.msgId)
        for attachment in email:
            # skip if the attachment has already been downloaded
            if (email.msgId + attachment.filename) in records:
                logger.info(
                    "Attachment already downloaded, skipping. Email was: %s", email.subject)
                continue

            if contentType in attachment.contentType:
                logger.debug("Content-type string of attachment: %s",
                             attachment.contentType)
                mimetype = attachment.contentType.split(';')[0].strip()
                logger.debug("Mimetype determined to be: %s", mimetype)
                filename = attachment.filename
                if not attachment.filename:
                    extension = mimetypes.guess_extension(
                        mimetype)
                    if not extension:
                        logger.warning(
                            "Skipping attachment. Unable to determine extension from content-type for unnamed attachment in email: %s.", email.subject)
                    filename = email.subject + extension
                    logger.info(
                        "Attachment had no file name. It will be named: %s", filename)
                if filename:
                    # TODO: just proving a point, not a good way to do this, for now skipping
                    #  it seems some filenames may be files with parameters like in HTTP
                    #  so, should try to fix the filenames to be on what is allowable by the OS. Example:
                    # Content-Type: image/png; name="sys_attachment.do?sys_id=f2b51517db5f1700abe8a5f74b961956"
                    # Content-Transfer-Encoding: base64
                    # Content-Disposition: inline; filename="sys_attachment.do?sys_id=f2b51517db5f1700abe8a5f74b961956"
                    # Content-ID: <sys_attachment.dosys_idf2b51517db5f1700abe8a5f74b961956@SNC.84ec9c02de157ddb>
                    if '?' not in filename:
                        logger.debug("Filename: %s", filename)
                        diff = ''
                        if os.path.exists(''.join([downloadPath, filename])):
                            logger.info("Duplicate file %s found.", filename)
                            diff = str(time.time())+'-'

                        path = ''.join(
                            [downloadPath, diff, filename])
                        logger.info("Writing: %s", path)
                        f = open(path, 'wb')
                        f.write(attachment.bytes)
                        f.close()

                        records.append(email.msgId + attachment.filename)
                        # TODO: Could be more efficient, perhaps just append the last one
                        with open(recordFile, 'w') as recf:
                            recf.writelines("%s\n" %
                                            record for record in records)
                        recf.close()


def main():
    load_dotenv()
    logLevel = os.getenv('ATTACH_LOG_LEVEL', 'INFO')

    LOGFORMAT = "%(asctime)s %(levelname)s - %(name)s.%(funcName)s - %(message)s"
    logging.basicConfig(level=logLevel, format=LOGFORMAT)
    logging.getLogger('googleapiclient').setLevel(logging.WARNING)

    downloadPath = os.getenv('ATTACH_DOWNLOAD_PATH', './')
    if downloadPath[-1] != '/' and downloadPath[-1] != '\\':
        downloadPath = downloadPath + '/'
        if not os.path.isdir(downloadPath):
            logger.error(
                "Download directory does not exist, please create it first: %s", downloadPath)
            exit("Invalid download location proivded")
    appCredentials = os.getenv('ATTACH_APP_CREDENTIALS', './credentials.json')
    apiToken = os.getenv('ATTACH_API_TOKEN', './token.pickle')
    query = os.getenv('ATTACH_GMAIL_SEARCH', '')
    contentType = os.getenv('ATTACH_CONTENT_TYPE', '')
    recordPath = os.getenv('ATTACH_RECORD_PATH', './')
    if recordPath[-1] != '/' and recordPath[-1] != '\\':
        recordPath = recordPath + '/'
        if not os.path.isdir(recordPath):
            logger.error(
                "Record directory does not exist, please create it first: %s", recordPath)
            exit("Invalid Record location proivded")
    recordFile = recordPath + RECORD_FILENAME

    records = []
    if os.path.exists(recordFile):
        with open(recordFile, 'r') as frec:
            records = [record.rstrip() for record in frec.readlines()]

    creds = authenticate(apiToken, appCredentials)

    service = build(API_NAME, API_VER, credentials=creds,
                    cache_discovery=False)

    downloadAttachmentsFromGmail(
        service, downloadPath, recordFile, records, query, contentType)


if __name__ == '__main__':
    main()

# TODO: make parameters globally available, and commandline param settable
#   make the record file a globally known directory
# TODO: content-type filtering more flexible (perhaps regex, or list of types)
# TODO: comment
# TODO: document how to set up and create credentials
