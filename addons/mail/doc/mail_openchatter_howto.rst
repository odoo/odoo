
How to use OpenChatter in my addon
===================================

Running example
++++++++++++++++

A small my_task model will be used as example to explain how to use the
OpenChatter feature. Being simple, it has only the following fields:

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

Make your object inherit from :class:`mail.thread`::

  class my_task(osv.osv):
    _name = "my.task"
    _description = "My Task"
    # inherit from mail.thread allows the use of OpenChatter
    _inherit = ['mail.thread']

Use the thread viewer widget inside your form view by using the mail_thread
widget on the message_ids field inherited from :class:`mail.thread`::

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

When sending a notification is required in your workflow or business logic,
use :meth:`mail.thread.message_post`. It will automatically take care of
subscriptions and notifications.

Here is a small example of sending a notification when the ``do_something``
method is called::

  def do_something(self, cr, uid, ids, context=None):
      self.do_something_send_note(cr, uid, ids, context=context)
      return res

  def do_something_send_note(self, cr, uid, ids, context=None):
      self.message_post(
          cr, uid, ids, _('My subject'),
          _("has received a <b>notification</b> and is happy for it."),
          context=context)

Notifications guidelines
+++++++++++++++++++++++++

- avoid unnecessary content, swamping users with irrelevant messages will lead
  to them ignoring all messages
- use short sentences
- do not include the document name, this is done by the thread widget
- use a simple and clean style

   - html tags are supported: use <b> or <em> mainly
   - put key word(s) in bold
   - avoid fancy styles that will break the OpenERP look and feel
- create a separate method for sending your notification, use clear method
  names allowing quickly spotting notification code e.g. name notification
  methods by using the original method name postfixed by ``_send_note``
  (``do_something`` -> ``do_something_send_note``)

Subscription management
++++++++++++++++++++++++

The default subscription behavior is the following:

* Subscriptions are set up by creating a :class:`mail.followers`` entry
* If a user creates or updates a document, they automatically follow it. The
  corresponding :class:`mail.followers` entry is created
* If a user explicitly cliks on the document's :guilabel:`Follow` button,
  they follow the document. The corresponding :class:`mail.followers` entry
  is created
* If a user explicitly clicks on the document's :guilabel:`Unfollow` button,
  they stop following the document. The corresponding :class:`mail.followers`
  entry is deleted

You should not directly manipulate :class:`mail.followers` entry, if you need
to override the default subscription behavior you should override the relevant
:class:`mail.thread` methods.

.. TODO: wtf are the relevant mail.thread methds? message_get_subscribers
         has disappeared and nothing looks like a replacement
