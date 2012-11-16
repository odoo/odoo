.. _mail_message_subtype:

OpenChatter Pi (3.1415): Message Subtype
========================================

  To overcome the problems of crowdy walls in system notification, We have added features of **Message Subtype** in mail.

mail.message.subtype
++++++++++++++++++++
``mail.message.subtype`` has following fields:

 - ``Name``: fields.char(' Message Subtype ', size = 128,required = True,help = 'Subtype Of Message'),
 - ``model_ids``: fields.many2many('ir.model','mail_message_subtyp_message_rel','message_subtype_id', 'model_id', 'Model',help = "link some subtypes to several models, for projet/task"),
 - ``default``: fields.boolean('Default', help = "When subscribing to the document, users will receive by default messages related to this subtype unless they uncheck this subtype"),

mail.followers
++++++++++++++

In ``mail.followers`` we have added additional many2many field subtype ids :

 - ``subtype_ids``: fields.many2many('mail.message.subtype','mail_message_subtyp_rel','subscription_id', 'subtype_id', 'Subtype',help = "linking some subscription to several subtype for projet/task")

mail.message
++++++++++++

In mail_message we have added additional field subtype_id which Indicates the Type of Message

 - ``subtype_id``: fields.many2one('mail.message.subtype', 'Subtype')

mail.thread
+++++++++++

 - In **message_post** method add the *subtype_id* field as parameter and set as default subtype 'Other'.
 
        def message_post(self, cr, uid, thread_id, body='', subject=False, msg_type='notification', parent_id=False, attachments=None, subtype='other', context=None, ``**kwargs``):

 - In **message_subscribe** method add the *subtype_ids* field as parameter.In this method if subtype_ids is None, it fatch the default true subtypes in mail.message.subtypes otherwise pass selected subtypes.
   For update subtypes call **message_subscribe_udpate_subtypes** method

        def message_subscribe(self, cr, uid, ids, partner_ids,subtype_ids = None, context=None):

 - Add **message_subscribe_udpate_subtypes** method to update the subtype_ids in followers.

    def message_subscribe_udpate_subtypes(self, cr, uid, ids, user_id, subtype_ids,context=None):
        followers_obj = self.pool.get('mail.followers')
        followers_ids = followers_obj.search(cr, uid, [('res_model', '=', self._name), ('res_id', 'in', ids)])
        return followers_obj.write(cr, uid, followers_ids, {'subtype_ids': [(6, 0 , subtype_ids)]}, context = context)

For Each Addons:
++++++++++++++++

 - Add data of subtypes for each addons module.
 - Add subtype field as parameter in **message_post** Method for each addons module.

How It Works:
+++++++++++++

 - In addons module when we Follow a Perticular document It display under the followers button.
 - In sybtypes there are 3 default subtypes for each addons
    1) Email
    2) Comment
    3) Other
 - In document display a default subtypes(which are true) related a perticular model_ids wise.
    
    Example:-
        If I have open crm.lead, It display only subtypes of crm.lead

 - When we select subtype it update subtype_ids(which are checked) in mail.follower where match res_model & res_id of the current documents.
 - when message created update subtype_id of that message in mail.message.
 - In Feeds display only those notifications of documents which subtypes are selected
