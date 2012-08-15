
How to use OpenChatter in my addon
===================================

Running example
++++++++++++++++

A small my_task model will be used as example to explain how to use the OpenChatter feature. Being simple, it has only the following fields :

 - a name
 - a task responsible
 - a related project

::

  class my_task(osv.osv):
    _name = "my.task"
    _description = "My Task"
    _columns = {
      'name': fields.char('Name', required=True, size=64),
      'user_id':fields.many2one('res.users', string='Responsible',
        ondelete='cascade', required=True, select=1),
      'project_id':fields.many2one('project.project', string='Related project',
        ondelete='cascade', required=True, select=1),
    }


Two-lines feature integration
++++++++++++++++++++++++++++++

Make your module inheriting from the ``mail.thread`` class.

::

  class my_task(osv.osv):
    _name = "my.task"
    _description = "My Task"
    # inherit from mail.thread allows the use of OpenChatter
    _inherit = ['mail.thread']

Use the thread viewer widget inside your form view by using the mail_thread widget on the message_ids field inherited from mail.thread.

::

  <record model="ir.ui.view" id="my_task_form_view">
    <field name="name">My Task</field>
    <field name="model">my.task</field>
    <field name="priority">1</field>
    <field name="arch" type="xml">
      <form>
      [...]
      <field name="message_ids" colspan="4" widget="mail_thread" nolabel="1"/>
      </form>
    </field>
  </record>

Send notifications
+++++++++++++++++++

When sending a notification is required in your workflow or business logic, use the ``message_append_note`` method. This method is a shortcut to the ``message_append`` method that takes all ``mail.message`` fields as arguments. This latter method calls ``message_create`` that

 - creates the message
 - parses the body to find users you want to push the message to (finding and parsing ``@login`` in the message body)
 - pushes a notification to users following the document and requested users of the latetr step

You should therefore not worry about subscriptions or anything else than sending the notification. Here is a small example of sending a notification when the ``do_something`` method is called : 

::

  def do_something(self, cr, uid, ids, context=None):
    [...]
    self.do_something_send_note(cr, uid, ids, context=context)
    [...]
    return res

  def do_something_send_note(self, cr, uid, ids, context=None):
    self.message_append_note(cr, uid, ids, _('My subject'),
    _("has received a <b>notification</b> and is happy for it."), context=context)

Notifications guidelines
+++++++++++++++++++++++++

Here are a few guidelines that you should keep in mind during the addition of system notifications :

 - avoid unnecessary content; if a message has no interest, do not implement it
 - use short sentences
 - do not include the document name, as it is managed by the thread widget
 - use a simple and clean style

   - html tags are supported: use <b> or <em> mainly
   - put main word(s) in bold
   - avoid fancy styles that will break the OpenERP look and feel
 - create a separate method for sending your notification

   - use a method name like ``original_method_name_send_note``, that allow to easily spot notification methods in the code

Subscription management
++++++++++++++++++++++++

There are a few default subscription tricks that you should know before playing with subscription:

 - users that click on 'follow' follow the document. An entry in ``mail.subscription`` is created.
 - users that click on 'unfollow' are no longer followers to the document. The related entry in ``mail.subscription`` is created.
 - users that create or update a document automatically follow it. An entry in ``mail.subscription`` is created.

If you want to override this default behavior, you should avoid doing it manualle. You should instead override the ``message_get_subscribers`` method from mail.thread. The default implementation looks in the ``mail.suscription`` table for entries matching ``user_id=uid, res_model=self._name, res_id=current_record_id``. You can add subscribers by overriding the ``message_get_subscribers`` and adding user ids to the returned list. This means that they will be considered as followers even if they do not have an entry in the mail.subscription table.

As an exemple, let us say that you want to automatically add the my_task responsible along with the project manager to the list of followers. The method could look like:

::

  def message_get_subscribers(self, cr, uid, ids, context=None):
    # get the followers from the mail.subscription table
    sub_ids = self.message_get_subscribers_ids(cr, uid, ids, context=context);
    # add the employee and its manager if specified to the subscribed users
    for obj in self.browse(cr, uid, ids, context=context):
      if obj.user_id:
        sub_ids.append(obj.user_id)
      if obj.project_id and obj.project_id.user_id:
        sub_ids.append(obj.project_id.user_id)
    return self.pool.get('res.users').read(cr, uid, sub_ids, context=context)

This method has the advantage of being able to implement a particular behavior with as few code addition as possible. Moreover, when changing the task responsible of the project manager, the subscribers are always correct. This allows to avoid to implement complex corner cases that could obfuscate the code.

The drawback of this method is that it is no longer possible to those subscribers to unfollow a document. Indeed, as user ids are added directly in a list in ``message_get_subscribers``, it is not possible to unsubscribe to a document. However, this drawback is mitigated by

 - only important users shoudl be added using this method. Important users should not unsubscribe from their documents.
 - users can hide the notifications on their Wall

Messages display management
++++++++++++++++++++++++++++

By default, the mail_thread widget shows all messages related to the current document beside the document, in the History and comments section. However, you may want to display other messages in the widget. For example, the OpenChatter on res.users model shows

 - messages related to the user, as usual (messages with ``model = res.users, res_id = current_document_id``)
 - messages directly pushed to this user (containing @login)

The best way to direct the messages that will be displayed in the OpenChatter widget is to override the ``message_load`` method. For example, the following method fetches messages as usual, but also fetches messages linked to the task project that contain the task name. Please refer to the API for more details about the arguments.

::

  def message_load(self, cr, uid, ids, limit=100, offset=0, domain=[], ascent=False, root_ids=[False], context=None):
    msg_obj = self.pool.get('mail.message')
    for my_task in self.browse(cr, uid, ids, context=context):
      # search as usual messages related to the current document
      msg_ids += msg_obj.search(cr, uid, ['|', '&', ('res_id', '=', my_task.id), ('model', '=', self._name),
        # add: search in the current task project messages
        '&', '&', ('res_id', '=', my_task.project_id.id), ('model', '=', 'project.project'),
        # ... containing the task name
        '|', ('body_text', 'like', '%s' % (my_task.name)), ('body_html', 'like', '%s' % (my_task.name))
        ] + domain, limit=limit, offset=offset, context=context)
    # if asked: add ancestor ids to have complete threads
    if (ascent): msg_ids = self._message_add_ancestor_ids(cr, uid, ids, msg_ids, root_ids, context=context)
    return msg_obj.read(cr, uid, msg_ids, context=context)
