# Overview
This is a Django project built to track trades of shares between companies and people, and build PDF's for ledgers, registers, and certificates. The site lets you define companies, and then issue shares. Once shares are issued, the company can transfer them to people. When people hold shares, they can transfer between other people or companies.

# Transaction Chain Verification
The project properly verifies every trade issue or transfer. A person is not allows to transfer shares they dont own, and the current state of all transactions related to the company and share class being dealt with is guaranteed to be valid at all times. Users can freely go back and edit history, delete history, and add history and the system will confirm or deny their proposed changes only if the state of the whole transaction chain is confirmed to be valid after their change.

# Dependencies
The site is meant to be used in conjuction with nginx to host on a Linux VPS (Only tested with Ubuntu). The only dependencies to run the project are Python3 +, Django 2.2.12+, and an pytz 2023.3.post1+

# Screenshots

This picture shows the authorize and transfer share UI, as well as a generated PDF of an example certificate (once the 'Make Printable.')

<img width="1404" height="1352" alt="Overview" src="https://github.com/user-attachments/assets/319ee88b-fdb7-4d00-8e96-f146e31c2512" />

---

This picture shows the generated share ledger and share register PDS's (button and bread crumbs disappear once the 'Make Printable') button is clicked.


<img width="789" height="869" alt="ledger and redister" src="https://github.com/user-attachments/assets/f02dd56d-2441-4ca3-a72c-78ce3c597882" />

# To Do
- Update UI
- Incorporate hotkeys
- Host a demo version




