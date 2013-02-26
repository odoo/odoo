.. _mail_message:

mail.message
============

Models
++++++

``mail.message`` is a class for holding the main attributes of a message object
(notification for system message, reciving email message or sent messages). It 
could be reused as parent model for any database model, wall thread view, or 
wizard screen that needs to hold a kind of message.

All internal logic should be in a database-based model while this model 
holds the basics of a message. For example, a wizard for writing emails 
should inherit from this class.


.. versionchanged:: 7.0

ClientAction (ir.actions.client)
++++++++++++++++++++++++++++++++

.. code-block:: xml

     <record id="action_mail_inbox_feeds" model="ir.actions.client">
         <field name="name">Inbox</field>
         <field name="tag">mail.wall</field>
         <field name="res_model">mail.message</field>
         <field name="context"></field>
         <field name="params"></field>
         <field name="help" type="html"></field>
     </record>

 - ``tag`` : 'mail.wall', 'mail_thread' or 'mail.widget'
      'mail.wall' to have a display like the mail wall with threads, title, search view 
         (default value like a wall)
      'mail_thread' widget for field on standard view. (default value like a thread for 
         record, view on flat mode, no reply, no read/unread)
      'mail.widget' it's the root thread, used by 'mail.wall' and 'mail_thread'

 - ``help`` : Text HTML to display if there are no message
 - ``context`` : insert 'default_model' and 'default_res_id'
 - ``params`` : options for the widget
      - ``domain`` : choose the domain of the messages
      - ``truncate_limit`` : {Number} number of character to display before having a "show more" 
         link; note that the text will not be truncated if it does not have 110% of the parameter
      - ``show_record_name`` : {Boolean} display the name and link of the related record
      - ``show_reply_button`` : {Boolean} display the reply button
      - ``show_read_unread_button`` : {Boolean} display the read/unread button
      - ``display_indented_thread`` : {int [0,1]} number thread level to indented threads.
      - ``show_compose_message`` : display the composer on top thread
      - ``show_compact_message`` : display the compact message on the thread when the user clic 
         on this compact mode, the composer is open
      - ``message_ids`` : {Array | False} List of ids to fetch by the root thread. If no value,
         the root search the message by the domain
      - ``compose_placeholder`` : Message to display on the textareaboxes.
      - ``show_link`` : Display partner (authors, followers...) on link or not
      - ``compose_as_todo`` : The root composer mark automatically the message as todo
      - ``readonly`` : Read only mode, hide all action buttons and composer

Fields
++++++

 - ``type`` : usually 'email', 'comment', 'notification'.
   Message type: email for external email message recieve, notification for system
   message, comment for other messages such as user replies.
 - ``subtype_id`` :
   Subtype of the notification for system message. The users can followe a document
   and choose the subtype of this document (eg: Create, Comment, Done).
   You can defined new subtypes and choose his name, by agreement the id begin by "mt\_" on the model
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
