==================
High-level ORM API
==================

.. _compute:

Computed fields: defaults and function fields
=============================================

The high-level API attempts to unify concepts of programmatic value generation
for function fields (stored or not) and default values through the use of
computed fields.

Fields are marked as computed by setting their ``compute`` attribute to the
name of the method used to compute then::

    has_sibling = fields.Integer(compute='compute_has_sibling')

by default computation methods behave as simple defaults in case no
corresponding value is found in the database::

    def default_number_of_employees(self):
        self.number_of_employees = 1

.. todo::

    literal defaults::

        has_sibling = fields.Integer(compute=fields.default(1))

but they can also be used for computed fields by specifying fields used for
the computation. The dependencies can be dotted for "cascading" through
related models::

    @api.depends('parent_id.children_count')
    def compute_has_sibling(self):
        self.has_sibling = self.parent_id.children_count >= 2

.. todo::

    function-based::

        has_sibling = fields.Integer()
        @has_sibling.computer
        @api.depends('parent_id.children_count')
        def compute_has_sibling(self):
            self.has_sibling = self.parent_id.children_count >= 2

note that computation methods (defaults or others) do not *return* a value,
they *set*  values the current object. This means the high-level API does not
need :ref:`an explicit multi <fields-functional>`: a ``multi`` method is
simply one which computes several values at once::

    @api.depends('company_id')
    def compute_relations(self):
        self.computed_company = self.company_id
        self.computed_companies = self.company_id.to_recordset()

Automatic onchange
==================

Using to the improved and expanded :ref:`computed fields <compute>`, the
high-level ORM API is able to infer the effect of fields on
one another, and thus automatically provide a basic form of onchange without
having to implement it by hand, or implement dozens of onchange functions to
get everything right.




.. todo::

    deferred records::

        partner = Partner.record(42, defer=True)
        partner.name = "foo"
        partner.user_id = juan
        partner.save() # only saved to db here

        with scope.defer():
            # all records in this scope or children scopes are deferred
            #   until corresponding scope poped or until *this* scope poped?
            partner = Partner.record(42)
            partner.name = "foo"
            partner.user_id = juan
        # saved here, also for recordset &al, ~transaction

        # temp deferment, maybe simpler? Or for bulk operations?:
        with Partner.record(42) as partner:
            partner.name = "foo"
            partner.user_id = juan

    ``id = False`` => always defered? null v draft?

.. todo:: keyword arguments passed positionally (common for context, completely breaks everything)

.. todo:: optional arguments (report_aged_receivable)

.. todo:: non-id ids? (mail thread_id)

.. todo:: partial signatures on overrides (e.g. message_post)

.. todo::

    ::

        field = fields.Char()

        @field.computer
        def foo(self):
            "compute foo here"

    ~

    ::

        field = fields.Char(compute='foo')

        def foo(self):
            "compute foo here"

.. todo:: doc

.. todo:: incorrect dependency spec?

.. todo:: dynamic dependencies?

    ::

        @api.depends(???)
        def foo(self)
            self.a = self[self.b]

.. todo:: recursive onchange

    Country & state. Change country -> remove state; set state -> set country

.. todo:: onchange list affected?
