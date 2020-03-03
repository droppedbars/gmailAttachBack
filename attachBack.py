from __future__ import print_function

import base64
import logging
import os.path
import pickle
import pprint
import time

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

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


def getHeaderInfo(message):
    for header in message['payload']['headers']:
        if header['name'] == 'Subject':
            subject = header['value']
        if header['name'] == 'Date':
            date = header['value']
    return date, subject


def downloadAttachmentsFromGmail(service):
    messagelist = service.users().messages().list(userId='me').execute()
    for messageMeta in messagelist['messages']:
        message = service.users().messages().get(
            userId='me', id=messageMeta['id']).execute()

        id = messageMeta['id']
        subject = ''
        contentType = ''
        filename = ''
        date = ''

        date, subject = getHeaderInfo(message)

        logger.debug("Checking message: %s from %s", subject, date)
        if 'parts' in message['payload']:
            for part in message['payload']['parts']:
                for attachHeader in part['headers']:
                    if attachHeader['name'] == 'Content-Type':
                        contentType = attachHeader['value']
                if part['filename']:
                    filename = part['filename']
                if 'attachmentId' in part['body']:
                    # TODO: attachment is embedded, could use email subject and mimetime to set filename.ext
                    if not part['filename']:
                        filename = 'fakename-'+str(time.time())
                        logger.info(
                            "Attachment had no name. Named to %s from email subject %s", filename, subject)
                    attachmentId = part['body']['attachmentId']

                    logger.info(
                        "Downloading attachment: %s from email subject %s", filename, subject)
                    attachment = service.users().messages().attachments().get(
                        userId='me', messageId=id, id=attachmentId).execute()

                    file_data = base64.urlsafe_b64decode(
                        attachment['data'].encode('UTF-8'))

                    path = ''.join(['./fromgmail/', filename])

                    f = open(path, 'wb')
                    f.write(file_data)
                    f.close()


def main():
    LOGFORMAT = "%(asctime)s %(levelname)s - %(name)s.%(funcName)s - %(message)s"
    logging.basicConfig(level=logging.DEBUG, format=LOGFORMAT)

    creds = authenticate('token.pickle', 'credentials-gmail.json')

    service = build(API_NAME, API_VER, credentials=creds,
                    cache_discovery=False)

    downloadAttachmentsFromGmail(service)


if __name__ == '__main__':
    main()

# TODO: iterate through response pages from gamil
# TODO: create names based on subject and mimetype for unnamed attachments
# TODO: permit filtering based on mimetype (Eg, only download pictures), note, some are mimetype and some are mimetype and filename
# TODO: refactor into functions and such
# TODO: comment
# TODO: document how to set up and create credentials
# TODO: logger
# TODO: store messageids that have been downloaded to prevent re-downloading on future runs.
# TODO: configurable storage location
