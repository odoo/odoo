.. warning::

    Don't use this module if you're already running the regular ``queue_job`` runner.


For the easiest case, no configuration is required besides installing the module.

To avoid CronWorker CPU timeout from abruptly stopping the job processing cron, it's
recommended to launch Odoo with ``--limit-time-real-cron=0``, to disable the CronWorker
timeout altogether.

.. note::

    In Odoo.sh, this is done by default.


Parallel execution of jobs can be achieved by leveraging multiple ``ir.cron`` records:

* Make sure you have enough CronWorkers available (Odoo CLI ``--max-cron-threads``)
* Duplicate the ``queue_job_cron`` cron record as many times as needed, until you have
  as much records as cron workers.
