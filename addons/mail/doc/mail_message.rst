.. _mail_message:

mail.message
============

Models
+++++++

``mail.message.common`` is an abstract class for holding the main attributes of a 
message object. It could be reused as parent model for any database model 
or wizard screen that needs to hold a kind of message.

All internal logic should be in a database-based model while this model 
holds the basics of a message. For example, a wizard for writing emails 
should inherit from this class and not from mail.message.


.. versionchanged:: 7.0

 - ``subtype`` is renamed to ``content_subtype``: usually 'html' or 'plain'.
   This field is used to select plain-text or rich-text contents accordingly.
 - ``subtype`` is moved to mail.message model. The purpose is to be able to 
   distinguish message of the same type, such as notifications about creating
   or cancelling a record. For example, it is used to add the possibility 
   to hide notifications in the wall.

Those changes aim at being able to distinguish the message content to the
message itself.

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
