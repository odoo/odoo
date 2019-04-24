:banner: banners/security.jpg

.. _reference/security:

================
Security in Odoo
================

Aside from manually managing access using custom code, Odoo provides two main
data-driven mechanisms to manage or restrict access to data.

Both mechanisms are linked to specific users through *groups*: a user belongs
to any number of groups, and security mechanisms are associated to groups,
thus applying security mechamisms to users.

.. note:: Since Odoo 12.0, basic access controls have to be defined for
    new models or their views won't be accessible !
    If no access control is specified for a model, a warning will be raised in
    the server logs and propose basic read rules to provide minimal read access to
    the models.

.. _reference/security/acl:

Access Control
==============

Managed by the ``ir.model.access`` records, defines access to a whole model.

Each access control has a model to which it grants permissions, the
permissions it grants and optionally a group.

Access controls are additive, for a given model a user has access all
permissions granted to any of its groups: if the user belongs to one group
which allows writing and another which allows deleting, they can both write
and delete.

If no group is specified, the access control applies to all users, otherwise
it only applies to the members of the given group.

Available permissions are creation (``perm_create``), searching and reading
(``perm_read``), updating existing records (``perm_write``) and deleting
existing records (``perm_unlink``)

.. _reference/security/rules:

Record Rules
============

Record rules are conditions that records must satisfy for an operation
(create, read, update or delete) to be allowed. It is applied record-by-record
after access control has been applied.

A record rule has:

* a model on which it applies
* a set of permissions to which it applies (e.g. if ``perm_read`` is set, the
  rule will only be checked when reading a record)
* a set of user groups to which the rule applies, if no group is specified
  the rule is *global*
* a :ref:`domain <reference/orm/domains>` used to check whether a given record
  matches the rule (and is accessible) or does not (and is not accessible).
  The domain is evaluated with two variables in context: ``user`` is the
  current user's record and ``time`` is the `time module`_

Global rules and group rules (rules restricted to specific groups versus
groups applying to all users) are used quite differently:

* Global rules are subtractive, they *must all* be matched for a record to be
  accessible
* Group rules are additive, if *any* of them matches (and all global rules
  match) then the record is accessible

This means the first *group rule* restricts access, but any further
*group rule* expands it, while *global rules* can only ever restrict access
(or have no effect).

.. code-block:: xml

  <record id="only_responsible_can_modify" model="ir.rule">
    <field name="name">Only Responsible can modify Course</field>
    <field name="model_id" ref="model_openacademy_course"/>
    <field name="groups" eval="[(4, ref('openacademy.group_maesters'))]"/>
    <field name="perm_read" eval="0"/>
    <field name="perm_write" eval="1"/>
    <field name="perm_create" eval="1"/>
    <field name="perm_unlink" eval="1"/>
    <field name="domain_force">
       [('responsible_id','=',user.id)]
    </field>
  </record>

.. warning:: record rules do not apply to the Administrator user
    :class: aphorism

.. _reference/security/fields:

Field Access
============

.. .. versionadded:: 7.0

An ORM :class:`~odoo.fields.Field` can have a ``groups`` attribute
providing a list of groups (as a comma-separated string of
:term:`external identifiers`).

If the current user is not in one of the listed groups, he will not have
access to the field:

* restricted fields are automatically removed from requested views
* restricted fields are removed from :meth:`~odoo.models.Model.fields_get`
  responses
* attempts to (explicitly) read from or write to restricted fields results in
  an access error

.. todo::

    field access groups apply to administrator in fields_get but not in
    read/write...

.. _time module: https://docs.python.org/3/library/time.html

.. _reference/security/guidelines:

Security guidelines
===================

Do not bypass the ORM
~~~~~~~~~~~~~~~~~~~~~
You should never use the database cursor directly when the ORM can do the same
thing! By doing so you are bypassing all the ORM features, possibly the
transactions, access rights and so on.

And chances are that you are also making the code harder to read and probably
less secure.

.. code-block:: python

    # very very wrong
    self.env.cr.execute('SELECT id FROM auction_lots WHERE auction_id in (' + ','.join(map(str, ids))+') AND state=%s AND obj_price > 0', ('draft',))
    auction_lots_ids = [x[0] for x in self.env.cr.fetchall()]

    # no injection, but still wrong
    self.env.cr.execute('SELECT id FROM auction_lots WHERE auction_id in %s '\
               'AND state=%s AND obj_price > 0', (tuple(ids), 'draft',))
    auction_lots_ids = [x[0] for x in self.env.cr.fetchall()]

    # better
    auction_lots_ids = self.search([('auction_id','in',ids), ('state','=','draft'), ('obj_price','>',0)])


No SQL injections, please !
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Care must be taken not to introduce SQL injections vulnerabilities when using
manual SQL queries. The vulnerability is present when user input is either
incorrectly filtered or badly quoted, allowing an attacker to introduce
undesirable clauses to a SQL query (such as circumventing filters or
executing UPDATE or DELETE commands).

The best way to be safe is to never, NEVER use Python string concatenation (+)
or string parameters interpolation (%) to pass variables to a SQL query string.

The second reason, which is almost as important, is that it is the job of the
database abstraction layer (psycopg2) to decide how to format query parameters,
not your job! For example psycopg2 knows that when you pass a list of values
it needs to format them as a comma-separated list, enclosed in parentheses !

.. code-block:: python

    # the following is very bad:
    #   - it's a SQL injection vulnerability
    #   - it's unreadable
    #   - it's not your job to format the list of ids
    self.env.cr.execute('SELECT distinct child_id FROM account_account_consol_rel ' +
               'WHERE parent_id IN ('+','.join(map(str, ids))+')')

    # better
    self.env.cr.execute('SELECT DISTINCT child_id '\
               'FROM account_account_consol_rel '\
               'WHERE parent_id IN %s',
               (tuple(ids),))

This is very important, so please be careful also when refactoring, and most
importantly do not copy these patterns!

Here is a memorable example to help you remember what the issue is about (but
do not copy the code there). Before continuing, please be sure to read the
online documentation of pyscopg2 to learn how to use it properly:

- The problem with query parameters (http://initd.org/psycopg/docs/usage.html#the-problem-with-the-query-parameters)
- How to pass parameters with psycopg2 (http://initd.org/psycopg/docs/usage.html#passing-parameters-to-sql-queries)
- Advanced parameter types (http://initd.org/psycopg/docs/usage.html#adaptation-of-python-values-to-sql-types)

Never commit the transaction
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Odoo framework is in charge of providing the transactional context for
all RPC calls. The principle is that a new database cursor is opened at the
beginning of each RPC call, and committed when the call has returned, just
before transmitting the answer to the RPC client, approximately like this:

.. code-block:: python

    def execute(self, db_name, uid, obj, method, *args, **kw):
        db, pool = pooler.get_db_and_pool(db_name)
        # create transaction cursor
        cr = db.cursor()
        try:
            res = pool.execute_cr(cr, uid, obj, method, *args, **kw)
            cr.commit() # all good, we commit
        except Exception:
            cr.rollback() # error, rollback everything atomically
            raise
        finally:
            cr.close() # always close cursor opened manually
        return res

If any error occurs during the execution of the RPC call, the transaction is
rolled back atomically, preserving the state of the system.

Similarly, the system also provides a dedicated transaction during the execution
of tests suites, so it can be rolled back or not depending on the server
startup options.

The consequence is that if you manually call ``cr.commit()`` anywhere there is
a very high chance that you will break the system in various ways, because you
will cause partial commits, and thus partial and unclean rollbacks, causing
among others:

#. inconsistent business data, usually data loss
#. workflow desynchronization, documents stuck permanently
#. tests that can't be rolled back cleanly, and will start polluting the
   database, and triggering error (this is true even if no error occurs
   during the transaction)

Here is the very simple rule:
    You should **NEVER** call ``cr.commit()`` yourself, **UNLESS** you have
    created your own database cursor explicitly! And the situations where you
    need to do that are exceptional!

    And by the way if you did create your own cursor, then you need to handle
    error cases and proper rollback, as well as properly close the cursor when
    you're done with it.

And contrary to popular belief, you do not even need to call ``cr.commit()``
in the following situations:
- in the ``_auto_init()`` method of an *models.Model* object: this is taken
care of by the addons initialization method, or by the ORM transaction when
creating custom models
- in reports: the ``commit()`` is handled by the framework too, so you can
update the database even from within a report
- within *models.Transient* methods: these methods are called exactly like
regular *models.Model* ones, within a transaction and with the corresponding
``cr.commit()/rollback()`` at the end
- etc. (see general rule above if you have in doubt!)

All ``cr.commit()`` calls outside of the server framework from now on must
have an **explicit comment** explaining why they are absolutely necessary, why
they are indeed correct, and why they do not break the transactions. Otherwise
they can and will be removed !

Further information
-------------------

Take a look at `Odoo's 10 rules <https://www.odoo.com/r/h3s>`_ for safer code.
