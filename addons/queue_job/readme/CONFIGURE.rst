* Using environment variables and command line:

  * Adjust environment variables (optional):

    - ``ODOO_QUEUE_JOB_CHANNELS=root:4`` or any other channels configuration.
      The default is ``root:1``

    - if ``xmlrpc_port`` is not set: ``ODOO_QUEUE_JOB_PORT=8069``

  * Start Odoo with ``--load=web,queue_job``
    and ``--workers`` greater than 1. [1]_

* Keep in mind that the number of workers should be greater than the number of
  channels. ``queue_job`` will reuse normal Odoo workers to process jobs. It
  will not spawn its own workers.

* Using the Odoo configuration file:

.. code-block:: ini

  [options]
  (...)
  workers = 6
  server_wide_modules = web,queue_job

  (...)
  [queue_job]
  channels = root:2

* Environment variables have priority over the configuration file.

* Confirm the runner is starting correctly by checking the odoo log file:

.. code-block::

  ...INFO...queue_job.jobrunner.runner: starting
  ...INFO...queue_job.jobrunner.runner: initializing database connections
  ...INFO...queue_job.jobrunner.runner: queue job runner ready for db <dbname>
  ...INFO...queue_job.jobrunner.runner: database connections ready

* Create jobs (eg using ``base_import_async``) and observe they
  start immediately and in parallel.

* Tip: to enable debug logging for the queue job, use
  ``--log-handler=odoo.addons.queue_job:DEBUG``

.. [1] It works with the threaded Odoo server too, although this way
       of running Odoo is obviously not for production purposes.

* Be sure to check out *Jobs Garbage Collector* CRON and change *enqueued_delta* and *started_delta* parameters to your needs.

  * ``enqueued_delta``: Spent time in minutes after which an enqueued job is considered stuck.
    Set it to 0 to disable this check.
  * ``started_delta``: Spent time in minutes after which a started job is considered stuck.
    This parameter should not be less than ``--limit-time-real // 60`` parameter in your configuration.
    Set it to 0 to disable this check. Set it to -1 to automate it, based in the server's ``--limit-time-real`` config parameter.

  .. code-block:: python

    # `model` corresponds to 'queue.job' model
    model.requeue_stuck_jobs(enqueued_delta=1, started_delta=-1)
