# gmailAttachBack
Attachment backup from gmail accounts.

# Permitting gmailAttachBack to access your Gmail
1. Open web browser to Google API Console: https://console.developers.google.com/apis
2. Select the Project dropdown and click NEW PROJECT
3. Name the project
4. Click + ENABLE APIS AND SERVICSE
5. Search for GMAIL, select it and click ENABLE
6. From the Overview click CREATE CREDENTIALS
7. For the question "Which API are you using?" select Gmail API
8. For the question "Where will you be calling the API From?" select Other UI
9. For the question "What data will you be accessing?" select User data
10. Click the button "Which Credentials do I need?"
11. Click SET UP CONSENT SCREEN
12. For User Type select Internal (this restricts the app to you and your organization's users)
13. Fill out the consent screen information, App Name, icon, etc
14. For the Scope select "../auth/gmail.readonly
15. It is not necessary to fill out the various URLs
16. Go to CREDENTIALS
17. + CREATE CREDENTIAL, OAuth Client ID
18. Application Type: Other
19. Name the application
20. Download the client secret json file and store it somewhere the application will be able to access it
21. If there is a token.pickle file, delete it
22. Set the environment variable ATTACH_APP_CREDENTIALS to be the path an file name of the client secret json you downloaded.
23. Run the application
24. The application will attempt to open a web browser to a URL. If it does not, you can get the URL from the console.
25. In the webpage, follow the prompts to authorize the application
26. Close the web browser when finished
27. The app will run.

# Environment Variables
The application behaviour can be modified by setting environment variables:
ATTACH_LOG_LEVEL
* Defines the log level, options are DEBUG, INFO, WARNING, ERROR, CRITICAL
* Default value is INFO
ATTACH_DOWNLOAD_PATH
* The location where the downloaded attachments will be put. If the location does not exist or has permissions incorrect, then the application will fail.
* Default value is the same directory that the application is in.
ATTACH_RECORD_PATH
* Sets the location where a file named records.txt will be created to store a listing of attachments that were downloaded. In subsequent runs if an attachment appears in this file, it will not be downloaded again. To re-download attachments, delete this file, or remove entries from it.
* Default value is the same directory that the application is in.
ATTACH_APP_CREDENTIALS
* Path and filename to the secrets file downloaded above when enable API access to Gmail
* If this file is invalid, or does not exist, the application will fail.
* Default value is ./credentials.json
ATTACH_API_TOKEN
* Path and filename to the access credentials obtained during OAuth negotiation.
* If this file is deleted, you will need to reauthorize the application to access your Gmail.
* Default value is ./token.pickle
ATTACH_GMAIL_SEARCH
* Search parameters for email. This is the same syntax as searching from within Gmail and is useful for restricting the number of emails the application will need to access.
* No default value
ATTACH_CONTENT_TYPE
* Restricts file types to be downloaded based on the content-type of the file. It is a simply substring search. So "image" would be true for "image/jpeg". "pdf" would be true for "application/pdf"
* No default value

