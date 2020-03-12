#from __future__ import print_function

import base64
import json
import logging
import mimetypes
import os
import os.path
import pickle
import pprint
import re
import time

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from emailMsg import Attachment, Email, EmailMsg, GoogleAuth

logger = logging.getLogger("attachBack")

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

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

    # Load the secrets
    with open(credFileName, 'r') as json_file:
        client_config = json.load(json_file)
        logger.info("App secrets read from %s", credFileName)

    # TODO: deal with failure
    auth = GoogleAuth(SCOPES, GoogleAuth.API_GMAIL,
                      GoogleAuth.API_VER_1, client_config, creds)

    # Save the credentials for the next run
    with open(tokenFileName, 'wb') as token:
        pickle.dump(auth.creds, token)
        logger.info("Credentials saved to %s for future use.",
                    tokenFileName)
    logging.info("Successfully authenticated to gmail.")
    return auth


def isValidFileName(name: str):
    if not name:
        logger.debug("Testing filename failed on missing name.")
        return False

    # reg check for invalid characters: [\\\/:\"\?<>|]+
    p = re.compile(r"[\\\/:\"\?<>|]+")
    if p.search(name):
        logger.deug(
            "Testing filename failed on invalid character \\/:\"?<>| : %s", name)
        return False

    # check that filename doesn't end in a . and the extension doesn't end in a .
    chunks = name.split('.')
    if len(chunks) > 0 and not chunks[-1]:
        logger.debug(
            "Testing filename failed on extension or filename ended in period: %s", name)
        return False
    if len(chunks) > 2 and not chunks[-2]:
        logger.debug(
            "Testing filename failed on filename ended in period: %s", name)
        return False

    return True


def downloadAttachmentsFromGmail(auth, downloadPath: str, recordFile: str, records: list, query: str = '', contentType: str = ''):
    emails = Email(auth, query=query)

    for email in emails:
        logger.debug("Email ID: %s Subject: %s", email.msgId, email.subject)
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

                logger.debug("Attachment filename: %s", attachment.filename)
                # if there's no filename or its invalid, we make one up and guess the extension from content-type
                if not attachment.filename or not isValidFileName(attachment.filename):
                    extension = mimetypes.guess_extension(
                        mimetype)
                    if not extension:
                        logger.warning(
                            "Skipping attachment. Unable to determine extension from content-type for unnamed attachment in email: %s.", email.subject)
                        continue

                    filename = "temp" + str(time.time()) + extension
                    logger.info("Invalid name: %s - new name: %s",
                                attachment.filename, filename)
                if filename:
                    logger.debug("Filename: %s", filename)

                    # create a name modifier if there's already a file with the same name
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
                    with open(recordFile, 'w', encoding="utf-8") as recf:
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
        with open(recordFile, 'r', encoding="utf-8") as frec:
            records = [record.rstrip() for record in frec.readlines()]

    auth = authenticate(apiToken, appCredentials)

    downloadAttachmentsFromGmail(
        auth, downloadPath, recordFile, records, query, contentType)


if __name__ == '__main__':
    main()

# TODO: make parameters globally available, and commandline param settable
#   make the record file a globally known directory
# TODO: content-type filtering more flexible (perhaps regex, or list of types)
# TODO: comment
# TODO: screenshots for setting up APIs and credentials
# TODO: set up imports file
# TODO: some code clean-up is needed
