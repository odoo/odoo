.. _workflows:

Workflows
=========

A workflow is a directed graph where the nodes are called "activities" and the
arcs are called "transitions".

- Activities define work that should be done within the OpenERP server, such as
  changing the state of some records, or sending mails.

- Transitions control how the workflow will go from activities to activities.

When defining a workflow, one can attach conditions, signals, and triggers to
transitions, so that the behavior of the workflow can depend on user actions
(such as clicking on a button), changes to records, or arbitrary Python code.

Basics
------

Defining a workflow with data files is straightforward: a record "workflow" is
needed together with records for the activities and the transitions. For
instance here is a simple sequence of two activities defined in XML::

    <record id="test_workflow" model="workflow">
        <field name="name">test.workflow</field>
        <field name="osv">test.workflow.model</field>
        <field name="on_create">True</field>
    </record>

    <record id="activity_a" model="workflow.activity">
        <field name="wkf_id" ref="test_workflow"/>
        <field name="flow_start">True</field>
        <field name="name">a</field>
        <field name="kind">function</field>
        <field name="action">print_a()</field>
    </record>
    <record id="activity_b" model="workflow.activity">
        <field name="wkf_id" ref="test_workflow"/>
        <field name="flow_stop">True</field>
        <field name="name">b</field>
        <field name="kind">function</field>
        <field name="action">print_b()</field>
    </record>

    <record id="trans_a_b" model="workflow.transition">
        <field name="act_from" ref="activity_a"/>
        <field name="act_to" ref="activity_b"/>
    </record>

A worfklow is always defined with respect to a particular model (the model is
given through the ``osv`` attribute on the ``workflow`` model). Methods
specified in the activities or transitions will be called on that model.

In the example code above, a workflow called "test_workflow" is created. It is
made up of two activies, named "a" and "b", and one transition, going from "a"
to "b".

The first activity has its ``flow_start`` attribute set to True so that OpenERP
knows where to start the workflow when it is instanciated. Because
``on_create`` is set to True on the workflow record, the workflow is
instanciated for each newly created record. (Otherwise, the workflow should be
created by other means, such as from some module Python code.)

When the workflow is instanciated, it will start by the "a" activity. That
activity is of kind ``function`` which means the action ``print_a()`` is a
method to be called on the ``test.workflow`` model (the usual ``cr, uid, ids,
context`` arguments are passed for you).

The transition between "a" and "b" does not specify any conditions. This means
the workflow instance will immediately progress from "a" to "b" (after "a" has
been processed), and thus also process the "b" activity.

Transitions
-----------

Transitions provide the control structures to orchestrate a workflow. When an
activity is completed, the workflow engine will try to get across transitions
departing from the completed activity, towards the next activities.  In their
simplest form they just link activities from one to the others (as in the
example above), and activities are processed as soon as the activities
preceding them are completed.

But instead of running all activities in one fell swoop, it is also possible to
block on transitions, going through them only when some criteria are met. Such
criteria are the conditions, the signals, and the triggers. They are detailed
in the next sections.

Conditions
''''''''''

When an activity has been completed, its outgoing transitions will be inspected
to see if it is possible for the workflow instance to proceed through them and
reach the next activities. When only a condition is defined (i.e. no signal or
trigger is defined), the condition is evaluated by OpenERP, and if it evaluates
to ``True``, the worklfow instance will go through.

By default, the ``condition`` attribute (i.e. the expression to be evaluated)
is just "True", which will trivially evaluate to ``True``.

Actually, the condition can be several lines long, and the value of the last
one will be used to test if the transition can be taken.

In the condition evaluation environment, several symbols are conveniently
defined:

- The  database cursor (``cr``),
- the user ID (``uid``), the record ID tied to the workflow instance (``id``),
- the user ID wrapped in a list (``ids``),
- the model name (``model``),
- the model instance (``obj``),
- all the model column names,
- and all the record (the one obtained by browsing the provided ID) attributes.

Signals
'''''''

In addition of a condition, a transition can specify a signal name. When such
signal name is present, the transition will not be taken directly (even if the
condition evaluates to true). Instead the transition will block, waiting to be
woken up.

To wake up a transition with a defined signal name, the signal must be sent to
the workflow. A common way to send a signal is to use a button in the web
interface, using the ``<button/>`` element with the signal name as the ``name``
attribute of the button.

.. note:: The condition is still evaluated when the signal is sent to the
    workflow instance.

Triggers
''''''''

With conditions that evaluate to false, transitions are not taken (and thus the
activity it leads to will not be processed). Still, the workflow instance can
get new chances to progress across that transition by providing so-called
triggers. The idea is that when the condition fails, triggers are recorded in
database. Later, it is possible to wake-up specifically the workflow instances
that installed those triggers, offering them a new chance to evaluation their
transition conditions. This mechnism makes it cheaper to wake-up workflow
instances by targetting just a few of them (those that have installed the
triggers) instead of all of them.

Triggers are recorded in database as record IDs (together with the model name)
and refer to the workflow instance waiting for them. The transition definition
can thus provide a Python expression (using the ``trigger_model`` attribute)
that when evaluated will return the record IDs. Unlike the other expressions
defined on the workflow, this one is evaluated with respect to a model that can
be chosen on a per-transition basis with the ``trigger_expression`` attribute.

.. note:: Note that triggers are not re-installed whenever the transition is
    re-tried.

Splitting and joining transitions
'''''''''''''''''''''''''''''''''

When multiple transitions leave the same activity, or lead to the same
activity, OpenERP provides some control about which transitions will be
crossed, or how the reached activity will be processed. The ``split_mode`` and
``join_mode`` attributes on the activity are used for such control.

Activities
----------

While the transitions can be seen as the control structure of the workflows,
activities are the place where everything happen, from changing record states
to sending email.

Different kind of activities exist: ``Dummy``, ``Function``, ``Subflow``, and
``Stop all``; different kind of activities can do different and they are
detailed below. 

In addition to the activity kind, activies have some properties, detailed in
the next sections.

Flow start and flow stop
''''''''''''''''''''''''

The ``flow_start`` attribute is a boolean value specifying if the activity
starts the workflow. Multiple activities can have the ``flow_start`` attribute
set to ``True`` and when instanciating a workflow for a record, OpenERP will
simply process all of them, and try all their outgoing transitions afterwards.

The ``flow_stop`` attribute is also a boolean value, specifying if the activity
ends the workflow. A workflow is considered to be completed when all its
activities with the ``flow_stop`` attribute set to ``True`` are completed.

It is important for OpenERP to know when a workflow instance is completed: a
workflow can have an activity that is actually another workflow (called a
subflow) and that activity will be completed only when the subflow is
completed.

Subflow
'''''''

An activity can embed a complete workflow, called a subflow (the embedding
workflow is called the parent workflow). The workflow to instanciate is
specified by the ``subflow_id`` attribute.

.. note:: In the GUI, that attribute can not be set unless the kind of the
    activity is ``Subflow``.

The activity will be completed (and its outgoing transitions will be tried)
when the subflow is completed (see the ``flow_stop`` attribute above to read
about when a workflow is considered completed by OpenERP).

Sending a signal from a subflow
'''''''''''''''''''''''''''''''

When a workflow is used (as a sublfow) in the activity of a (parent) workflow,
the sublow can send a signal from its own activities to the parent by specifying a
signal name in the ``signal_send`` attribute. OpenERP will process those
activities normally and send to the parent workflow instance a signal with
``signal_send`` value prefixed with ``subflow.``.

In other words, it is possible to react and take transitions in the parent
workflow as activities are executed in the sublow.

Server actions
''''''''''''''

An activity can run a "Server Action" by specifying its ID in the ``action_id``
attribute.

Python action
'''''''''''''

An activity can run some Python code, provided through the ``action``
attribute. See the section about transition conditions to read about the
evaluation environment.

Split mode
''''''''''

After an activity has been processed, its outgoing transitions will be tried.
Normally, if a transition can be taken, OpenERP will do it and proceed to the
activity the transition leads to.

Actually, when more than a single transition is leaving an activity, OpenERP
can proceed, or not, depending on the other transitions. That is, the condition
on the transitions can be combined together, and the combined result will
instruct OpenERP to cross zero, one, or all the transitions. The way they are
combined is controlled by the ``split_mode`` attribute.

There are indeed three modes to decide how to combine the transition
conditions, ``XOR``, ``OR``, and ``AND``.

``XOR``
    When the transitions are combined with a ``XOR`` split mode, as soon as a
    transition with a condition that evaluates to true is found, the
    transition is taken and the other will not be tried.

``OR``
    With an ``OR`` mode, all the transitions with a condition that evaluates to
    true are taken. The remaining transitions will not be tried later.

``AND``
   With an ``AND`` mode, OpenERP will wait for all transition conditions to
   evaluate to true, then cross all the transitions at the same time.

Join mode
'''''''''

Just as departing transition conditions can be combined together to decide
whether they can be taken or not, arriving transitions can be combined together
to decide if an activity must be run. The attribute to control that behavior is
called ``join_mode``.

The join mode is a bit simpler than the split mode: only two modes are
provided, ``XOR`` and ``AND``.

``XOR``
    An activity with a ``XOR`` join mode will be run as soon as a transition is
    crossed to arrive at the activity.

``AND``
   With an ``AND`` mode, the activity will wait for all its incoming
   transitions to be crossed before being run.

Kinds
'''''

Activities can be of different kinds: ``dummy``, ``function``, ``subflow``, or
``stopall``. The kind defines what type of work an activity can do.

Dummy
    The ``dummy`` kind is for activities that do nothing (i.e. they act as hubs
    to gather/dispatch transitions), or for activities that only call a Server
    Action.

Function
    The ``function`` kind is for activities that only need to run some Python
    code, and possibly a Server Action.

Stop all
    The ``stopall`` kind is for activities that will completely halt the
    workflow instance. In addition they can also run some Python code.

Subflow
    When the kind of the activity is  ``subflow``, the activity will run
    another workflow. When the sub-workflow is completed, the activity will also be
    considered completed.

    Normally the sub-workflow is instanciated for the same record as the parent
    workflow. It is possible to change that default behavior by providing
    Python code that has to return a record ID for which a workflow has been
    instanciated.
