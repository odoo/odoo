This addon adds an integrated Job Queue to Odoo.

It allows to postpone method calls executed asynchronously.

Jobs are executed in the background by a ``Jobrunner``, in their own transaction.

Example:

.. code-block:: python

  from odoo import models, fields, api

  class MyModel(models.Model):
     _name = 'my.model'

     def my_method(self, a, k=None):
         _logger.info('executed with a: %s and k: %s', a, k)


  class MyOtherModel(models.Model):
      _name = 'my.other.model'

      def button_do_stuff(self):
          self.env['my.model'].with_delay().my_method('a', k=2)


In the snippet of code above, when we call ``button_do_stuff``, a job **capturing
the method and arguments** will be postponed.  It will be executed as soon as the
Jobrunner has a free bucket, which can be instantaneous if no other job is
running.


Features:

* Views for jobs, jobs are stored in PostgreSQL
* Jobrunner: execute the jobs, highly efficient thanks to PostgreSQL's NOTIFY
* Channels: give a capacity for the root channel and its sub-channels and
  segregate jobs in them. Allow for instance to restrict heavy jobs to be
  executed one at a time while little ones are executed 4 at a times.
* Retries: Ability to retry jobs by raising a type of exception
* Retry Pattern: the 3 first tries, retry after 10 seconds, the 5 next tries,
  retry after 1 minutes, ...
* Job properties: priorities, estimated time of arrival (ETA), custom
  description, number of retries
* Related Actions: link an action on the job view, such as open the record
  concerned by the job
