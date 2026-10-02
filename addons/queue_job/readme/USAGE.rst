To use this module, you need to:

#. Go to ``Job Queue`` menu

Developers
~~~~~~~~~~

Delaying jobs
-------------

The fast way to enqueue a job for a method is to use ``with_delay()`` on a record
or model:


.. code-block:: python

   def button_done(self):
       self.with_delay().print_confirmation_document(self.state)
       self.write({"state": "done"})
       return True

Here, the method ``print_confirmation_document()`` will be executed asynchronously
as a job. ``with_delay()`` can take several parameters to define more precisely how
the job is executed (priority, ...).

All the arguments passed to the method being delayed are stored in the job and
passed to the method when it is executed asynchronously, including ``self``, so
the current record is maintained during the job execution (warning: the context
is not kept).

Dependencies can be expressed between jobs. To start a graph of jobs, use ``delayable()``
on a record or model. The following is the equivalent of ``with_delay()`` but using the
long form:

.. code-block:: python

   def button_done(self):
       delayable = self.delayable()
       delayable.print_confirmation_document(self.state)
       delayable.delay()
       self.write({"state": "done"})
       return True

Methods of Delayable objects return itself, so it can be used as a builder pattern,
which in some cases allow to build the jobs dynamically:

.. code-block:: python

    def button_generate_simple_with_delayable(self):
        self.ensure_one()
        # Introduction of a delayable object, using a builder pattern
        # allowing to chain jobs or set properties. The delay() method
        # on the delayable object actually stores the delayable objects
        # in the queue_job table
        (
            self.delayable()
            .generate_thumbnail((50, 50))
            .set(priority=30)
            .set(description=_("generate xxx"))
            .delay()
        )

The simplest way to define a dependency is to use ``.on_done(job)`` on a Delayable:

.. code-block:: python

    def button_chain_done(self):
        self.ensure_one()
        job1 = self.browse(1).delayable().generate_thumbnail((50, 50))
        job2 = self.browse(1).delayable().generate_thumbnail((50, 50))
        job3 = self.browse(1).delayable().generate_thumbnail((50, 50))
        # job 3 is executed when job 2 is done which is executed when job 1 is done
        job1.on_done(job2.on_done(job3)).delay()

Delayables can be chained to form more complex graphs using the ``chain()`` and
``group()`` primitives.
A chain represents a sequence of jobs to execute in order, a group represents
jobs which can be executed in parallel. Using ``chain()`` has the same effect as
using several nested ``on_done()`` but is more readable. Both can be combined to
form a graph, for instance we can group [A] of jobs, which blocks another group
[B] of jobs. When and only when all the jobs of the group [A] are executed, the
jobs of the group [B] are executed. The code would look like:

.. code-block:: python

   from odoo.addons.queue_job.delay import group, chain

   def button_done(self):
       group_a = group(self.delayable().method_foo(), self.delayable().method_bar())
       group_b = group(self.delayable().method_baz(1), self.delayable().method_baz(2))
       chain(group_a, group_b).delay()
       self.write({"state": "done"})
       return True

When a failure happens in a graph of jobs, the execution of the jobs that depend on the
failed job stops. They remain in a state ``wait_dependencies`` until their "parent" job is
successful. This can happen in two ways: either the parent job retries and is successful
on a second try, either the parent job is manually "set to done" by a user. In these two
cases, the dependency is resolved and the graph will continue to be processed. Alternatively,
the failed job and all its dependent jobs can be canceled by a user. The other jobs of the
graph that do not depend on the failed job continue their execution in any case.

Note: ``delay()`` must be called on the delayable, chain, or group which is at the top
of the graph. In the example above, if it was called on ``group_a``, then ``group_b``
would never be delayed (but a warning would be shown).


Enqueing Job Options
--------------------

* priority: default is 10, the closest it is to 0, the faster it will be
  executed
* eta: Estimated Time of Arrival of the job. It will not be executed before this
  date/time
* max_retries: default is 5, maximum number of retries before giving up and set
  the job state to 'failed'. A value of 0 means infinite retries.
* description: human description of the job. If not set, description is computed
  from the function doc or method name
* channel: the complete name of the channel to use to process the function. If
  specified it overrides the one defined on the function
* identity_key: key uniquely identifying the job, if specified and a job with
  the same key has not yet been run, the new job will not be created

Configure default options for jobs
----------------------------------

In earlier versions, jobs could be configured using the ``@job`` decorator.
This is now obsolete, they can be configured using optional ``queue.job.function``
and ``queue.job.channel`` XML records.

Example of channel:

.. code-block:: XML

    <record id="channel_sale" model="queue.job.channel">
        <field name="name">sale</field>
        <field name="parent_id" ref="queue_job.channel_root" />
    </record>

Example of job function:

.. code-block:: XML

    <record id="job_function_sale_order_action_done" model="queue.job.function">
        <field name="model_id" ref="sale.model_sale_order" />
        <field name="method">action_done</field>
        <field name="channel_id" ref="channel_sale" />
        <field name="related_action" eval='{"func_name": "custom_related_action"}' />
        <field name="retry_pattern" eval="{1: 60, 2: 180, 3: 10, 5: 300}" />
    </record>

The general form for the ``name`` is: ``<model.name>.method``.

The channel, related action and retry pattern options are optional, they are
documented below.

When writing modules, if 2+ modules add a job function or channel with the same
name (and parent for channels), they'll be merged in the same record, even if
they have different xmlids. On uninstall, the merged record is deleted when all
the modules using it are uninstalled.


**Job function: model**

If the function is defined in an abstract model, you can not write
``<field name="model_id" ref="xml_id_of_the_abstract_model"</field>``
but you have to define a function for each model that inherits from the abstract model.


**Job function: channel**

The channel where the job will be delayed. The default channel is ``root``.

**Job function: related action**

The *Related Action* appears as a button on the Job's view.
The button will execute the defined action.

The default one is to open the view of the record related to the job (form view
when there is a single record, list view for several records).
In many cases, the default related action is enough and doesn't need
customization, but it can be customized by providing a dictionary on the job
function:

.. code-block:: python

   {
       "enable": False,
       "func_name": "related_action_partner",
       "kwargs": {"name": "Partner"},
   }

* ``enable``: when ``False``, the button has no effect (default: ``True``)
* ``func_name``: name of the method on ``queue.job`` that returns an action
* ``kwargs``: extra arguments to pass to the related action method

Example of related action code:

.. code-block:: python

    class QueueJob(models.Model):
        _inherit = 'queue.job'

        def related_action_partner(self, name):
            self.ensure_one()
            model = self.model_name
            partner = self.records
            action = {
                'name': name,
                'type': 'ir.actions.act_window',
                'res_model': model,
                'view_type': 'form',
                'view_mode': 'form',
                'res_id': partner.id,
            }
            return action


**Job function: retry pattern**

When a job fails with a retryable error type, it is automatically
retried later. By default, the retry is always 10 minutes later.

A retry pattern can be configured on the job function. What a pattern represents
is "from X tries, postpone to Y seconds". It is expressed as a dictionary where
keys are tries and values are seconds to postpone as integers:


.. code-block:: python

   {
       1: 10,
       5: 20,
       10: 30,
       15: 300,
   }

Based on this configuration, we can tell that:

* 5 first retries are postponed 10 seconds later
* retries 5 to 10 postponed 20 seconds later
* retries 10 to 15 postponed 30 seconds later
* all subsequent retries postponed 5 minutes later

**Job Context**

The context of the recordset of the job, or any recordset passed in arguments of
a job, is transferred to the job according to an allow-list.

The default allow-list is `("tz", "lang", "allowed_company_ids", "force_company", "active_test")`. It can
be customized in ``Base._job_prepare_context_before_enqueue_keys``.
**Bypass jobs on running Odoo**

When you are developing (ie: connector modules) you might want
to bypass the queue job and run your code immediately.

To do so you can set `QUEUE_JOB__NO_DELAY=1` in your enviroment.

**Bypass jobs in tests**

When writing tests on job-related methods is always tricky to deal with
delayed recordsets. To make your testing life easier
you can set `queue_job__no_delay=True` in the context.

Tip: you can do this at test case level like this

.. code-block:: python

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(
            cls.env.context,
            queue_job__no_delay=True,  # no jobs thanks
        ))

Then all your tests execute the job methods synchronously
without delaying any jobs.

Testing
-------

**Asserting enqueued jobs**

The recommended way to test jobs, rather than running them directly and synchronously is to
split the tests in two parts:

 * one test where the job is mocked (trap jobs with ``trap_jobs()`` and the test
   only verifies that the job has been delayed with the expected arguments
 * one test that only calls the method of the job synchronously, to validate the
   proper behavior of this method only

Proceeding this way means that you can prove that jobs will be enqueued properly
at runtime, and it ensures your code does not have a different behavior in tests
and in production (because running your jobs synchronously may have a different
behavior as they are in the same transaction / in the middle of the method).
Additionally, it gives more control on the arguments you want to pass when
calling the job's method (synchronously, this time, in the second type of
tests), and it makes tests smaller.

The best way to run such assertions on the enqueued jobs is to use
``odoo.addons.queue_job.tests.common.trap_jobs()``.

Inside this context manager, instead of being added in the database's queue,
jobs are pushed in an in-memory list. The context manager then provides useful
helpers to verify that jobs have been enqueued with the expected arguments. It
even can run the jobs of its list synchronously! Details in
``odoo.addons.queue_job.tests.common.JobsTester``.

A very small example (more details in ``tests/common.py``):

.. code-block:: python

    # code
    def my_job_method(self, name, count):
        self.write({"name": " ".join([name] * count)

    def method_to_test(self):
        count = self.env["other.model"].search_count([])
        self.with_delay(priority=15).my_job_method("Hi!", count=count)
        return count

    # tests
    from odoo.addons.queue_job.tests.common import trap_jobs

    # first test only check the expected behavior of the method and the proper
    # enqueuing of jobs
    def test_method_to_test(self):
        with trap_jobs() as trap:
            result = self.env["model"].method_to_test()
            expected_count = 12

            trap.assert_jobs_count(1, only=self.env["model"].my_job_method)
            trap.assert_enqueued_job(
                self.env["model"].my_job_method,
                args=("Hi!",),
                kwargs=dict(count=expected_count),
                properties=dict(priority=15)
            )
            self.assertEqual(result, expected_count)


     # second test to validate the behavior of the job unitarily
     def test_my_job_method(self):
         record = self.env["model"].browse(1)
         record.my_job_method("Hi!", count=12)
         self.assertEqual(record.name, "Hi! Hi! Hi! Hi! Hi! Hi! Hi! Hi! Hi! Hi! Hi! Hi!")

If you prefer, you can still test the whole thing in a single test, by calling
``jobs_tester.perform_enqueued_jobs()`` in your test.

.. code-block:: python

    def test_method_to_test(self):
        with trap_jobs() as trap:
            result = self.env["model"].method_to_test()
            expected_count = 12

            trap.assert_jobs_count(1, only=self.env["model"].my_job_method)
            trap.assert_enqueued_job(
                self.env["model"].my_job_method,
                args=("Hi!",),
                kwargs=dict(count=expected_count),
                properties=dict(priority=15)
            )
            self.assertEqual(result, expected_count)

            trap.perform_enqueued_jobs()

            record = self.env["model"].browse(1)
            record.my_job_method("Hi!", count=12)
            self.assertEqual(record.name, "Hi! Hi! Hi! Hi! Hi! Hi! Hi! Hi! Hi! Hi! Hi! Hi!")

**Execute jobs synchronously when running Odoo**

When you are developing (ie: connector modules) you might want
to bypass the queue job and run your code immediately.

To do so you can set ``QUEUE_JOB__NO_DELAY=1`` in your environment.

.. WARNING:: Do not do this in production

**Execute jobs synchronously in tests**

You should use ``trap_jobs``, really, but if for any reason you could not use it,
and still need to have job methods executed synchronously in your tests, you can
do so by setting ``queue_job__no_delay=True`` in the context.

Tip: you can do this at test case level like this

.. code-block:: python

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(
            cls.env.context,
            queue_job__no_delay=True,  # no jobs thanks
        ))

Then all your tests execute the job methods synchronously without delaying any
jobs.

In tests you'll have to mute the logger like:

    @mute_logger('odoo.addons.queue_job.models.base')

.. NOTE:: in graphs of jobs, the ``queue_job__no_delay`` context key must be in at
          least one job's env of the graph for the whole graph to be executed synchronously


Tips and tricks
---------------

* **Idempotency** (https://www.restapitutorial.com/lessons/idempotency.html): The queue_job should be idempotent so they can be retried several times without impact on the data.
* **The job should test at the very beginning its relevance**: the moment the job will be executed is unknown by design. So the first task of a job should be to check if the related work is still relevant at the moment of the execution.

Patterns
--------
Through the time, two main patterns emerged:

1. For data exposed to users, a model should store the data and the model should be the creator of the job. The job is kept hidden from the users
2. For technical data, that are not exposed to the users, it is generally alright to create directly jobs with data passed as arguments to the job, without intermediary models.
