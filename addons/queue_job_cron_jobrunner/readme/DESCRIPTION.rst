This module implements a simple ``queue.job`` runner using ``ir.cron`` triggers.

It's meant to be used on environments where the regular job runner can't be run, like
on Odoo.sh.

Unlike the regular job runner, where jobs are dispatched to the HttpWorkers, jobs are
processed on the CronWorker threads by the job runner crons. This is a design decision
because:

* Odoo.sh puts HttpWorkers to sleep when there's no network activity
* HttpWorkers are meant for traffic. Users shouldn't pay the price of background tasks.

For now, it only implements the most basic features of the ``queue_job`` runner, notably
no channel capacity nor priorities. Please check the ROADMAP for further details.
