.. _mail_state:

message_unread
==============

``message_unread`` is a boolean field that states whether the document
has unread messages. In previous versions, some documents were going
back to ``pending`` state when receiving an email through the mail
gateway. Now the state related to messages differs from the state or
stage of the document itself.

message_unread and need action mechanism
++++++++++++++++++++++++++++++++++++++++

The ``mail`` module introduces a default behavior for the need_action
mechanism [REF].

::

  def get_needaction_user_ids(self, cr, uid, ids, context=None):
    """ Returns the user_ids that have to perform an action
        :return: dict { record_id: [user_ids], }
    """
    result = super(ir_needaction_mixin, self).get_needaction_user_ids(cr, uid, ids, context=context)
    for obj in self.browse(cr, uid, ids, context=context):
      if obj.message_unread == False and obj.user_id:
        result[obj.id].append(obj.user_id.id)
    return result
