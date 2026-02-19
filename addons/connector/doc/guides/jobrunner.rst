.. _jobrunner:


#######################################
Configuring channels and the job runner
#######################################

.. automodule:: odoo.addons.queue_job.jobrunner.runner


What is a channel?
------------------

.. autoclass:: odoo.addons.queue_job.jobrunner.channels.Channel
   :noindex:

How to configure Channels?
--------------------------

The ``ODOO_QUEUE_JOB_CHANNELS`` environment variable must be
set before starting Odoo in order to enable the job runner
and configure the capacity of the channels.

The general syntax is ``channel(.subchannel)*(:capacity(:key(=value)?)*)?,...``.

Intermediate subchannels which are not configured explicitly are autocreated
with an unlimited capacity (except the root channel which if not configured gets
a default capacity of 1).

A delay in seconds between jobs can be set at the channel level with
the ``throttle`` key.

Example ``ODOO_QUEUE_JOB_CHANNELS``:

* ``root:4``: allow up to 4 concurrent jobs in the root channel.
* ``root:4,root.sub:2``: allow up to 4 concurrent jobs in the root channel and
  up to 2 concurrent jobs in the channel named ``root.sub``.
* ``sub:2``: the same.
* ``root:4:throttle=2``: wait at least 2 seconds before starting the next job
