
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

from_address = "dan@tldrnewsletter.com"  # Change to desired sender
destination_folder = from_address



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
processed_uids = set()

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

        folder_text = folder.decode(errors='replace')
        mailbox = folder_text.split('"')[-2]

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

        # ====================================
        # STEP 3: SEARCH BY KEYWORD
        # ====================================

        # status, data = conn.uid(
        #     'SEARCH',
        #     None,
        #     'BODY',
        #     f'"{keyword}"'
        # )

        # keyword_uids = set(
        #     data[0].split() if status == 'OK' and data[0] else []
        # )

        # ====================================
        # STEP 4: SEARCH BY FROM ADDRESS
        # ====================================

        sender_uids = set()
        if from_address:

            status, data = conn.uid(
                'SEARCH',
                None,
                'FROM',
                f'"{from_address}"'
            )

            if status == 'OK' and data[0]:
                sender_uids = set(data[0].split())

        # Combine both searches (OR)
        matching_uids = sender_uids

        # print("Keyword matches:", len(keyword_uids))
        print("Sender matches:", len(sender_uids))
        print("Unique matches:", len(matching_uids))

        # ====================================
        # STEP 5: PROCESS MATCHES
        # ====================================

        for uid in sorted(
            matching_uids,
            key=lambda x: int(x)
        ):

            if uid in processed_uids:
                continue

            processed_uids.add(uid)

            status, response = conn.uid(
                'FETCH',
                uid,
                '(UID BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE MESSAGE-ID)])'
            )

            if status != 'OK':
                continue

            header_found = False

            for item in response:

                if isinstance(item, tuple):

                    header_found = True

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

            if not header_found:
                continue

            total_found += 1

            # ====================================
            # STEP 6: MOVE EMAIL
            # ====================================

            status, response = conn.uid(
                'MOVE',
                uid,
                f'"{destination_folder}"'
            )

            if status == 'OK':

                total_moved += 1

                print("Successfully moved!")
                print(f"Progress: {total_moved}")

            else:

                print("Move failed:", response)

    # ====================================
    # STEP 7: FINAL REPORT
    # ====================================

    print("\n========== FINAL REPORT ==========")

    print("From address:", from_address)
    print("Destination folder:", destination_folder)
    print("Emails processed:", total_found)
    print("Emails moved:", total_moved)

finally:

    conn.logout()

print("\nComplete!")
