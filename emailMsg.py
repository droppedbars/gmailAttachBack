import base64
import json
import logging
import os
import pickle
import pprint

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


class GoogleAuth():
    API_GMAIL = 'gmail'
    API_VER_1 = 'v1'

    # TODO: deal with failure to refresh
    # TODO: deal with user does not authorize
    def __init__(self, scopes: str, apiName: str, apiVer: str, secrets: json, creds: Credentials = None):
        self.logger = logging.getLogger(
            "emailMsg." + self.__class__.__name__)

        # TODO: value checks for missing parameters

        self.__apiVer = apiVer
        self.__apiName = apiName

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                self.logger.debug(
                    "Credentials were expired, attempting to refresh.")
                creds.refresh(Request())
            else:
                self.logger.info(
                    "Credentials could not be found, asking for authorization from the user.")
                flow = InstalledAppFlow.from_client_config(
                    secrets, scopes)
                creds = flow.run_local_server(port=0)
        self.creds = creds

    def buildService(self):
        service = build(self.__apiName, self.__apiVer, credentials=self.creds,
                        cache_discovery=False)
        return service


class Attachment():
    def __init__(self, auth, msgId: str, attachmentId: str, fileName: str, userId: str = 'me', contentType: str = None):
        self.logger = logging.getLogger(
            "emailMsg." + self.__class__.__name__)
        if not auth:
            raise ValueError("Valid GoogleAuth required for attachment.")
        if not msgId:
            raise ValueError("Valid msgId required for attachment.")
        if not attachmentId:
            raise ValueError("Valid attachmentId required for attachment.")

        self.id = attachmentId
        self.msgId = msgId
        self.__auth = auth
        self.filename = fileName
        self.__userId = userId
        self.contentType = contentType

        attachment = self.__auth.buildService().users().messages().attachments().get(
            userId=userId, messageId=msgId, id=attachmentId).execute()
        self.bytes = base64.urlsafe_b64decode(
            attachment['data'].encode('UTF-8'))
        self.__size = attachment['size']


class EmailMsg():
    def __init__(self, auth: GoogleAuth, msgId: str, userId: str = 'me'):
        self.logger = logging.getLogger(
            "emailMsg." + self.__class__.__name__)

        if not auth:
            raise ValueError("Valid GoogleAuth required for email.")
        if not msgId:
            raise ValueError("Valid msgId required for email.")

        self.__auth = auth
        self.__userId = userId
        self.msgId = msgId

        message = self.__auth.buildService().users().messages().get(
            userId=userId, id=msgId).execute()

        self.date, self.sender, self.subject = self.__getHeaderInfo(message)
        # TODO: get the actual email body in here
        self.__attachments = self.__getAttachments(message)
        self.__attachmentIndex = 0

    def __getHeaderInfo(self, message):
        for header in message['payload']['headers']:
            if header['name'] == 'Subject':
                subject = header['value']
            if header['name'] == 'Date':
                date = header['value']
            if header['name'] == 'From':
                sender = header['value']
        return date, sender, subject

    def __getAttachments(self, message):
        attachmentList = []
        if 'parts' in message['payload']:
            for part in message['payload']['parts']:
                filename = ''
                contentType = ''
                size = None
                for attachHeader in part['headers']:
                    if attachHeader['name'] == 'Content-Type':
                        contentType = attachHeader['value']
                if 'filename' in part and part['filename']:
                    filename = part['filename']
                if 'attachmentId' in part['body']:
                    attachmentId = part['body']['attachmentId']
                    if 'size' in part['body'] and part['body']['size']:
                        size = int(part['body']['size'])
                    attachment = {'id': attachmentId, 'filename': filename,
                                  'content-type': contentType, 'size': size}
                    attachmentList.append(attachment)
        return attachmentList

    def __iter__(self):
        return self

    def __next__(self):
        length = len(self.__attachments)
        if length <= 0 or length <= self.__attachmentIndex:
            raise StopIteration()
        attachment = Attachment(self.__auth, self.msgId,
                                self.__attachments[self.__attachmentIndex]['id'],
                                self.__attachments[self.__attachmentIndex]['filename'],
                                self.__userId, self.__attachments[self.__attachmentIndex]['content-type'])
        self.__attachmentIndex += 1
        return attachment


class Email():
    def __init__(self, auth: GoogleAuth, userId: str = 'me', query: str = None):
        self.logger = logging.getLogger(
            "emailMsg." + self.__class__.__name__)

        if not auth:
            raise ValueError("Valid GoogleAuth required for email.")

        self.__auth = auth
        self.__userId = userId
        self.__query = query

        messagelist = self.__auth.buildService().users().messages().list(
            userId=self.__userId, q=self.__query).execute()
        if 'messages' in messagelist:
            self.__messages = messagelist['messages']
        else:
            self.__messages = list()
        self.__nextPageToken = None
        if 'nextPageToken' in messagelist:
            self.__nextPageToken = messagelist['nextPageToken']

    def __iter__(self):
        return self

    def __next__(self):
        if len(self.__messages) <= 0:
            if not self.__nextPageToken:
                raise StopIteration
            messagelist = self.__auth.buildService().users().messages().list(
                userId='me', pageToken=self.__nextPageToken, q=self.__query).execute()
            if 'messages' in messagelist:
                self.__messages = messagelist['messages']
            else:
                self.__messages = list()
            self.__nextPageToken = None
            if 'nextPageToken' in messagelist:
                self.__nextPageToken = messagelist['nextPageToken']
        messageIds = self.__messages.pop(0)
        message = EmailMsg(self.__auth, messageIds['id'], self.__userId)
        return message


def authenticate(scopes: list, tokenFileName: str, credFileName: str):
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(tokenFileName):
        with open(tokenFileName, 'rb') as token:
            creds = pickle.load(token)
            # logger.info("Credentials read from %s", tokenFileName)

    # Load the secrets
    with open(credFileName, 'r') as json_file:
        client_config = json.load(json_file)
        # logger.info("App secrets read from %s", credFileName)

    # TODO: deal with failure
    auth = GoogleAuth(scopes, GoogleAuth.API_GMAIL,
                      GoogleAuth.API_VER_1, client_config, creds)

    # Save the credentials for the next run
    with open(tokenFileName, 'wb') as token:
        pickle.dump(auth.creds, token)
        # logger.info("Credentials saved to %s for future use.",
        #            tokenFileName)
    logging.info("Successfully authenticated to gmail.")
    return auth


def main():
    LOGFORMAT = "%(asctime)s %(levelname)s - %(name)s.%(funcName)s - %(message)s"
    logging.basicConfig(level=logging.WARNING, format=LOGFORMAT)

    auth = authenticate(['https://www.googleapis.com/auth/gmail.readonly'],
                        'token.pickle', 'credentials-gmail.json')

    service = auth.buildService()

    emailMsg = EmailMsg(auth, '170938527ac31a43')

    for attachment in emailMsg:
        print(attachment.filename)
        path = ''.join(['./fromgmail/', attachment.filename])

        f = open(path, 'wb')
        f.write(attachment.bytes)
        f.close()

    emails = Email(auth, query='has:attachment')

    for email in emails:
        print(email.sender)


if __name__ == '__main__':
    main()

# TODO: move authentication so that it just receives the json and doesn't require files, and is in the class
# TODO: build the service in the class
# TODO: debug logging
# TODO: error handling on failed calls
# TODO: documenting
# TODO: deleting an email
