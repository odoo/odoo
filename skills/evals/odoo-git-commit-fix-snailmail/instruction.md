We fixed a bug in the Odoo checkout at /app (branch 20.0-snailmail-cover-fva) but the change is not committed yet. Please commit the pending changes on the current branch with a proper commit message. Do not push.

Context, from the support ticket opw-6425088:

When the snailmail cover page is enabled on the company and a letter is sent by post to a German partner that has a "Street 2", the generated cover page prints the zip/city line twice. Pingen then rejects the letter because the address does not meet the Deutsche Post requirements.
