.. _api-queue:

#####
Queue
#####

Models
******

.. automodule:: odoo.addons.queue_job.models.base
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: odoo.addons.queue_job.models.queue_job

   .. autoclass:: QueueJob

     .. autoattribute:: _name
     .. autoattribute:: _inherit

***
Job
***

.. automodule:: odoo.addons.queue_job.job

   Decorators
   ==========

   .. autofunction:: job
   .. autofunction:: related_action

   Internals
   =========

   .. autoclass:: DelayableRecordset
      :members:
      :undoc-members:
      :show-inheritance:

   .. autoclass:: Job
      :members:
      :undoc-members:
      :show-inheritance:
