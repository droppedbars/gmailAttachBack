import base64
import logging
import os
import pickle
import pprint

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


class Attachment():
    def __init__(self, service, msgId: str, attachmentId: str, fileName: str, userId: str = 'me', contentType: str = None):
        self.logger = logging.getLogger(
            "emailMsg." + self.__class__.__name__)
        if not service:
            raise ValueError("Valid service required for attachment.")
        if not msgId:
            raise ValueError("Valid msgId required for attachment.")
        if not attachmentId:
            raise ValueError("Valid attachmentId required for attachment.")

        self.__id = attachmentId
        self.__msgId = msgId
        self.__service = service
        self.filename = fileName
        self.__userId = userId
        self.contentType = contentType

        attachment = service.users().messages().attachments().get(
            userId=userId, messageId=msgId, id=attachmentId).execute()
        self.bytes = base64.urlsafe_b64decode(
            attachment['data'].encode('UTF-8'))
        self.__size = attachment['size']


class EmailMsg():
    def __init__(self, service, msgId: str, userId: str = 'me'):
        self.logger = logging.getLogger(
            "emailMsg." + self.__class__.__name__)

        if not service:
            raise ValueError("Valid service required for email.")
        if not msgId:
            raise ValueError("Valid msgId required for email.")

        message = service.users().messages().get(
            userId=userId, id=msgId).execute()

        self.__msgId = msgId
        self.date, self.sender, self.subject = self.__getHeaderInfo(message)
        # TODO: get the actual email body in here
        self.__attachments = self.__getAttachments(message)
        self.__attachmentIndex = 0
        self.__service = service
        self.__userId = userId

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
        attachment = Attachment(self.__service, self.__msgId,
                                self.__attachments[self.__attachmentIndex]['id'],
                                self.__attachments[self.__attachmentIndex]['filename'],
                                self.__userId, self.__attachments[self.__attachmentIndex]['content-type'])
        self.__attachmentIndex += 1
        return attachment


class Email():
    def __init__(self, service, userId: str = 'me', query: str = None):
        self.logger = logging.getLogger(
            "emailMsg." + self.__class__.__name__)

        if not service:
            raise ValueError("Valid service required for email.")

        self.__service = service
        self.__userId = userId
        self.__query = query

        messagelist = service.users().messages().list(
            userId=self.__userId, q=self.__query).execute()
        self.__messages = messagelist['messages']
        self.__nextPageToken = None
        if 'nextPageToken' in messagelist:
            self.__nextPageToken = messagelist['nextPageToken']

    def __iter__(self):
        return self

    def __next__(self):
        if len(self.__messages) > 0:
            messageIds = self.__messages.pop(0)
            message = EmailMsg(self.__service, messageIds['id'], self.__userId)
            return message
        else:
            if not self.__nextPageToken:
                raise StopIteration
            messagelist = self.__service.users().messages().list(
                userId='me', pageToken=self.__nextPageToken, q=self.__query).execute()
            self.__messages = messagelist['messages']
            self.__nextPageToken = messagelist['nextPageToken']


def authenticate(tokenFileName: str, credFileName: str):
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(tokenFileName):
        with open(tokenFileName, 'rb') as token:
            creds = pickle.load(token)
            # logger.info("Credentials read from %s", tokenFileName)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # logger.info("Credentials were expired, attempting to refresh.")
            creds.refresh(Request())
        else:
            # logger.info(
            #    "Credentials could not be found, asking for authorization from the user.")
            flow = InstalledAppFlow.from_client_secrets_file(
                credFileName, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(tokenFileName, 'wb') as token:
            pickle.dump(creds, token)
            # logger.info("Credentials saved to %s for future use.",
            #            tokenFileName)
    logging.info("Successfully authenticated to gmail.")
    return creds


SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
API_NAME = 'gmail'
API_VER = 'v1'


def main():
    LOGFORMAT = "%(asctime)s %(levelname)s - %(name)s.%(funcName)s - %(message)s"
    logging.basicConfig(level=logging.WARNING, format=LOGFORMAT)

    creds = authenticate('token.pickle', 'credentials-gmail.json')

    service = build(API_NAME, API_VER, credentials=creds,
                    cache_discovery=False)

    emailMsg = EmailMsg(service, '170938527ac31a43')

    for attachment in emailMsg:
        print(attachment.filename)
        path = ''.join(['./fromgmail/', attachment.filename])

        f = open(path, 'wb')
        f.write(attachment.bytes)
        f.close()

    emails = Email(service, query='has:attachment')

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
