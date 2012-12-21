.. _mail_thread:

mail.thread and OpenChatter
===========================

API
+++

Writing messages and notifications
----------------------------------

``message_append``

Creates a new mail.message through message_create. The new message is attached 
to the current mail.thread, containing all the details passed as parameters. 
All attachments will be attached to the  thread record as well as to the 
actual message.

This method calls message_create that will handle management of subscription 
and notifications, and effectively create the message.

If ``email_from`` is not set or ``type`` not set as 'email', a note message 
is created (comment or system notification), without the usual envelope 
attributes (sender, recipients, etc.).

mail.group
++++++++++

A mail_group is a collection of users sharing messages in a discussion group. Group users are users that follow the mail group, using the subscription/follow mechanism of OpenSocial. A mail group has nothing in common wih res.users.group.
Additional information on fields:

 - ``member_ids``: user member of the groups are calculated with ``message_get_subscribers`` method from mail.thread
 - ``member_count``: calculated with member_ids
 - ``is_subscriber``: calculated with member_ids

res.users
+++++++++

OpenChatter updates the res.users class:
 - it adds a preference about sending emails when receiving a notification
 - make a new user follow itself automatically
 - create a welcome message when creating a new user, to make his arrival in OpenERP more friendly


Misc magic context keys
+++++++++++++++++++++++

 - mail_create_nosubscribe: when creating a new record that inherit from mail_thread,
   do not subscribe the creator to the document followers
 - mail_create_nolog: do not log creation message
 - mail_notify_noemail: do not send email notifications; partners to notify are
   notified, i.e. a mail_notification is created, but no email is actually send
