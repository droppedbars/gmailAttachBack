from __future__ import print_function

import base64
import os.path
import pickle
import pprint
import time

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

creds = None
# The file token.pickle stores the user's access and refresh tokens, and is
# created automatically when the authorization flow completes for the first
# time.
if os.path.exists('token.pickle'):
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)

# If there are no (valid) credentials available, let the user log in.
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials-gmail.json', SCOPES)
        creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open('token.pickle', 'wb') as token:
        pickle.dump(creds, token)

service = build('gmail', 'v1', credentials=creds)

messagelist = service.users().messages().list(userId='me').execute()
for messageMeta in messagelist['messages']:
    message = service.users().messages().get(
        userId='me', id=messageMeta['id']).execute()

    id = messageMeta['id']
    subject = ''
    contentType = ''
    filename = ''
    date = ''

    # pprint.pprint(message['payload']['headers'])

    for header in message['payload']['headers']:
        if header['name'] == 'Subject':
            subject = header['value']
        if header['name'] == 'Date':
            date = header['value']
    if 'parts' in message['payload']:
        for part in message['payload']['parts']:
            for attachHeader in part['headers']:
                if attachHeader['name'] == 'Content-Type':
                    contentType = attachHeader['value']
            if part['filename']:
                filename = part['filename']
                #print(date, '-', subject, '-', contentType, '-', filename)
            if 'attachmentId' in part['body']:
                print("foo: ", filename, contentType, subject)
                # TODO: attachment is embedded, could use email subject and mimetime to set filename.ext
                if not part['filename']:
                    filename = 'fakename-'+str(time.time())
                #    pprint.pprint(part)
                # print(part['body']['attachmentId'])
                attachmentId = part['body']['attachmentId']

                attachment = service.users().messages().attachments().get(
                    userId='me', messageId=id, id=attachmentId).execute()

                file_data = base64.urlsafe_b64decode(
                    attachment['data'].encode('UTF-8'))

                path = ''.join(['./fromgmail/', filename])

                f = open(path, 'wb')
                f.write(file_data)
                f.close()

# TODO: iterate through response pages from gamil
# TODO: create names based on subject and mimetype for unnamed attachments
# TODO: permit filtering based on mimetype (Eg, only download pictures), note, some are mimetype and some are mimetype and filename
# TODO: refactor into functions and such
# TODO: comment
# TODO: document how to set up and create credentials
# TODO: logger
