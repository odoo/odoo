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
