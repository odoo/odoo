The Odoo checkout at /app has a bug I'd like you to fix, then commit the fix on the current branch. Do not push.

The bug: when a tracked field changes on a record (for example the stage of a task, or the status of a sale order), followers who receive the change by email get a body like "DraftSales Order" + "Status" glued together: the arrow between the old and the new value and the parentheses around the field name are missing. In the chatter of the web client, the same message shows "Draft → Sales Order (Status)" correctly.
