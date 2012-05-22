.. _mail_thread:

mail.thread and OpenChatter
===========================

TODO

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
