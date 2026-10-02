* Support channel capacity and priority. (See ``_acquire_one_job``)
* Gracefully handle CronWorker CPU timeouts. (See ``_job_runner``)
* Commit transaction after job state updated to started. (See ``_process``)
