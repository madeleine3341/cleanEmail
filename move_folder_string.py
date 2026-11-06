
import imaplib
import environ
import email
from email.header import decode_header

# ====================================
# CONFIGURATION
# ====================================

env = environ.Env()
environ.Env.read_env()

user = env('EMAIL_USER')
password = env('EMAIL_PASSWORD')
imap_server = env('IMAP_SERVER')

keyword = "You have unread messages"
destination_folder = keyword
MAX_EMAILS = 1000


# ====================================
# HELPER FUNCTIONS
# ====================================

def decode_mime_header(value):

    if not value:
        return ""

    decoded_parts = decode_header(value)
    result = ""

    for part, encoding in decoded_parts:

        if isinstance(part, bytes):
            result += part.decode(
                encoding or 'utf-8',
                errors='replace'
            )
        else:
            result += part

    return result


# ====================================
# CONNECT TO YAHOO
# ====================================

conn = imaplib.IMAP4_SSL(imap_server, 993)
conn.login(user, password)

total_found = 0
total_moved = 0

try:

    # ====================================
    # STEP 1: CREATE DESTINATION FOLDER
    # ====================================

    status, folders = conn.list()

    if status != 'OK':
        raise Exception("Could not retrieve mailboxes")

    folder_exists = any(
        destination_folder.lower() in
        folder.decode(errors='replace').lower()
        for folder in folders
    )

    if not folder_exists:

        status, response = conn.create(
            f'"{destination_folder}"'
        )

        if status != 'OK':
            raise Exception("Could not create destination folder")

        print("Created folder:", destination_folder)

    else:
        print("Folder already exists:", destination_folder)

    # ====================================
    # STEP 2: SEARCH ALL MAILBOXES
    # ====================================

    status, folders = conn.list()

    print("\n========== SEARCHING ALL MAILBOXES ==========\n")

    for folder in folders:

        if total_moved >= MAX_EMAILS:
            break

        folder_text = folder.decode(errors='replace')
        mailbox = folder_text.split('"')[-2]

        # Skip destination folder
        if mailbox.lower() == destination_folder.lower():
            continue

        print(f"\nChecking mailbox: {mailbox}")

        status, data = conn.select(
            f'"{mailbox}"',
            readonly=False
        )

        if status != 'OK':
            print("Could not select mailbox")
            continue

        # Search email bodies
        status, data = conn.uid(
            'SEARCH',
            None,
            'BODY',
            f'"{keyword}"'
        )

        if status != 'OK':
            print("Search failed")
            continue

        email_uids = data[0].split() if data[0] else []

        print("Matching emails:", len(email_uids))

        # ====================================
        # STEP 3: PROCESS MATCHING EMAILS
        # ====================================

        for uid in email_uids:

            if total_moved >= MAX_EMAILS:
                break

            status, response = conn.uid(
                'FETCH',
                uid,
                '(UID BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE MESSAGE-ID)])'
            )

            if status != 'OK':
                continue

            for item in response:

                if isinstance(item, tuple):

                    header = email.message_from_bytes(item[1])

                    sender = decode_mime_header(
                        header.get('From', '')
                    )

                    subject = decode_mime_header(
                        header.get('Subject', '')
                    )

                    date = header.get('Date', '')

                    message_id = header.get('Message-ID', '')

                    print("\n------------------------------")
                    print("UID:", uid.decode())
                    print("Mailbox:", mailbox)
                    print("From:", sender)
                    print("Subject:", subject)
                    print("Date:", date)
                    print("Message-ID:", message_id)

            total_found += 1

            # ====================================
            # STEP 4: MOVE EMAIL
            # ====================================

            status, response = conn.uid(
                'MOVE',
                uid,
                f'"{destination_folder}"'
            )

            if status == 'OK':

                total_moved += 1

                print("Successfully moved!")
                print(
                    f"Progress: {total_moved}/{MAX_EMAILS}"
                )

            else:

                print("Move failed:", response)

    # ====================================
    # STEP 5: FINAL REPORT
    # ====================================

    print("\n========== FINAL REPORT ==========")

    print("Keyword:", keyword)
    print("Destination folder:", destination_folder)
    print("Maximum moves:", MAX_EMAILS)
    print("Emails processed:", total_found)
    print("Emails successfully moved:", total_moved)

finally:

    conn.logout()

print("\nComplete!")
