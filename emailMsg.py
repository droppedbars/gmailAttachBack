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
    """
    GoogleAuth handles authentication against Google APIs. It fronts the Google API Client
    Discovery components for building the authentication object given secrets and credetials.

    Attributes
    ----------
    creds : Credentials
        OAuth2 access and refresh tokens.
    """

    API_GMAIL = 'gmail'
    API_VER_1 = 'v1'

    # TODO: deal with failure to refresh
    # TODO: deal with user does not authorize
    def __init__(self, scopes: list, apiName: str, apiVer: str, secrets: json, creds: Credentials = None):
        # TODO: verify, should scopes be a list or a str?
        self.logger = logging.getLogger(
            "emailMsg." + self.__class__.__name__)

        if not scopes:
            raise ValueError("Valid scopes required.")
        if not apiName:
            raise ValueError("Valid apiName required.")
        if not apiVer:
            raise ValueError("Valid apiVer required.")
        if not secrets:
            raise ValueError("Valid secrets required.")

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
        """
        Returns a resource object for interacting with the Google API that the GoogleAuth object
        represents.

        Returns
        -------
        Resource object for interacting with the Google API.
        """

        service = build(self.__apiName, self.__apiVer, credentials=self.creds,
                        cache_discovery=False)
        return service


class Attachment():
    """
    Attachment represents a Gmail attachment.

    Attributes
    ----------
    id : str
        ID of the attachment
    msgId : str
        ID of the email that contains the attachment
    filename : str
        Filename of the attachment.
    contentType : str
        Content Type of the attachment.
    bytes : bytes
        Attachment data as bytes.
    """

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
    """
    EmailMsg represents a Gmail email message. EmailMsg is iterable to get the attachments associated
    with the email.

    Attributes
    ----------
    msgId : str
        ID of the email.
    date : str
        Date of receipt of the email.
    """

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
                    self.logger.debug(
                        "Attachment found for message: %s", attachment)
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
    """
    Email represents the user's Gmail contents. The emails can be iterated and the object will handle
    all necessary calls to the Gmail APIs to get them.
    """

    def __init__(self, auth: GoogleAuth, userId: str = 'me', query: str = None):
        self.logger = logging.getLogger(
            "emailMsg." + self.__class__.__name__)

        if not auth:
            raise ValueError("Valid GoogleAuth required for email.")

        self.__auth = auth
        self.__userId = userId
        self.__query = query
        self.__nextPageToken = None

        self.__loadPageOfMessages()

    def __loadPageOfMessages(self):
        self.logger.debug(
            "Retrieving page of messages with next page token of: %s", self.__nextPageToken)
        messagelist = self.__auth.buildService().users().messages().list(
            userId='me', pageToken=self.__nextPageToken, q=self.__query).execute()
        # TODO: deal with failure of the call above
        if 'messages' in messagelist:
            self.__messages = messagelist['messages']
        else:
            self.logger.debug("No messages returned from gmail.")
            self.__messages = list()
        self.__nextPageToken = None
        if 'nextPageToken' in messagelist:
            self.__nextPageToken = messagelist['nextPageToken']

    def __iter__(self):
        return self

    def __next__(self):
        if len(self.__messages) <= 0:
            self.logger.debug("No more messages in local list.")
            if not self.__nextPageToken:
                raise StopIteration
        self.__loadPageOfMessages()
        messageIds = self.__messages.pop(0)
        message = EmailMsg(self.__auth, messageIds['id'], self.__userId)
        return message


def __authenticate(scopes: list, tokenFileName: str, credFileName: str):
    """
    __authenticate is test code available for internal testing of the classes in emailMsg and not
    intended to be robust.
    """

    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(tokenFileName):
        with open(tokenFileName, 'rb') as token:
            creds = pickle.load(token)

    # Load the secrets
    with open(credFileName, 'r') as json_file:
        client_config = json.load(json_file)

    auth = GoogleAuth(scopes, GoogleAuth.API_GMAIL,
                      GoogleAuth.API_VER_1, client_config, creds)

    # Save the credentials for the next run
    with open(tokenFileName, 'wb') as token:
        pickle.dump(auth.creds, token)
    logging.info("Successfully authenticated to gmail.")
    return auth


def main():
    LOGFORMAT = "%(asctime)s %(levelname)s - %(name)s.%(funcName)s - %(message)s"
    logging.basicConfig(level=logging.WARNING, format=LOGFORMAT)

    auth = __authenticate(['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.metadata'],
                          'secrets/token.pickle', 'secrets/credentials-gmail.json')

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

# TODO: error handling on failed calls
