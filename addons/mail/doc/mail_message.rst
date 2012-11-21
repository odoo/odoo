.. _mail_message:

mail.message
============

Models
+++++++

``mail.message`` is a class for holding the main attributes of a message object
(notification for system message, reciving email message or sent messages). It 
could be reused as parent model for any database model, wall thread view, or 
wizard screen that needs to hold a kind of message.

All internal logic should be in a database-based model while this model 
holds the basics of a message. For example, a wizard for writing emails 
should inherit from this class.


.. versionchanged:: 7.0

Fields
+++++++

 - ``type`` : usually 'email', 'comment', 'notification'.
   Message type: email for external email message recieve, notification for system
   message, comment for other messages such as user replies.
 - ``subtype_id`` :
   Subtype of the notification for system message. The users can followe a document
   and choose the subtype of this document (eg: Create, Comment, Done).
   You can defined new subtypes and choose his name, by agreement the id begin by "mt_" on the model
   "mail.message.subtype".
 - ``partner_ids`` :
   List of recipients, the recipients have this message in their personal mailboxe.
 - ``notified_partner_ids`` :
   Partners that have a notification pushing this message in their mailboxes. Usualy 
   it's an automatic system message for a model followed by users.
 - ``notification_ids`` :
   Technical field holding the message notifications. Use notified_partner_ids to access 
   notified partners.
 - ``attachment_ids`` :
   List of attachments
 - ``parent_id`` :
   It's the initial thread message. It's use for group message by thread in mailboxes.
 - ``child_ids`` :
   List of child message linked to the initial thread message.
 - ``model`` :
   Related Document Moded. It's use for group message by document.
 - ``res_id`` :
   Related Document ID. It's use for group message by document.
 - ``record_name`` :
   Functionnal field use to get the name of related document.
 - ``vote_user_ids`` :
   List of partner that vote/like this message.
 - ``to_read`` :
   Functional field to search for messages the current user has to read. The messages as
   treat like a need action. When the user recive a message (to_read = True) this message
   or action must be performed and mark done (to_read = False)
 - ``favorite_user_ids`` :
   Users that set this message in their favorites/todo list.

Methods
+++++++

 - ``message_read`` :
   Value: ids, domain, message_unload_ids, thread_level, context, parent_id, limit
   Return: List of dictinary of message. All message is sent with their parented messages and
   sort by id. The messages that the user can read but not in his search, are group in
   expandable messages. The expandable messages contain the domain to expand.
 - ``check_access_rule`` :
   Overwrite the initial message for this model.