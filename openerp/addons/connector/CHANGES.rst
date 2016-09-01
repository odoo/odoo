Changelog
---------

.. Future (?)
.. ~~~~~~~~~~
.. 
.. * 

9.0.1.0.2 (2016-03-03)
~~~~~~~~~~~~~~~~~~~~~~

* Fix: adapt to upstream api change to obtain db connection (https://github.com/OCA/connector/pull/179)

9.0.1.0.1 (2016-03-03)
~~~~~~~~~~~~~~~~~~~~~~

* Enabled the JobRunner by default, with a default channels configuration of root:1
* Removed the old workers
* Removed the broken dbfilter support (https://github.com/OCA/connector/issues/58)
* Cleaned the methods that have been deprecated in version 3.x

8.0.3.3.0 (2016-02-29)
~~~~~~~~~~~~~~~~~~~~~~

* Allow to define seconds when raising a RetryableJobError (https://github.com/OCA/connector/pull/124)
* Allow to ignore the retry counter when raising a RetryableJobError (https://github.com/OCA/connector/pull/124)
* Add 'mock_job_delay_to_direct' to ease tests on jobs (https://github.com/OCA/connector/pull/123)
* Add helper function to acquire Posgres advisory locks (https://github.com/OCA/connector/pull/138, https://github.com/OCA/connector/pull/139)
* Improvement of 'is_module_installed' which now uses the registry instead of db + cache (https://github.com/OCA/connector/pull/130)
* Security: Prevent to unpickle globals which are not jobs or whitelisted types (https://github.com/OCA/connector/pull/170)
* Fix: Manage non-ascii Postgres errors (https://github.com/OCA/connector/pull/167)
* Fix: ignore dbfilter containing %d or %h (https://github.com/OCA/connector/pull/166)
* Fix: correctly obtain the list of database with odoo is started with --no-database-list (https://github.com/OCA/connector/pull/164)
* Fix: Set job back to 'pending' in case of exception (https://github.com/OCA/connector/pull/150, https://github.com/OCA/connector/pull/151, https://github.com/OCA/connector/pull/152, https://github.com/OCA/connector/pull/155)
* Fix: Clear environment caches and recomputations upon failures (https://github.com/OCA/connector/pull/131)
* Fix: when a job fails, inactive users are no longer added to its followers (https://github.com/OCA/connector/pull/137)
* Fix: Set job to failed after non-retryable OperationalError (https://github.com/OCA/connector/pull/132)
* Fix: wrong model in connector_base_product's views (https://github.com/OCA/connector/pull/119)
* Various documentation improvements


3.2.0 (2015-09-10)
~~~~~~~~~~~~~~~~~~

* method 'install_in_connector' is now deprecated (https://github.com/OCA/connector/pull/74)
* Add a retry pattern for jobs (https://github.com/OCA/connector/pull/75, https://github.com/OCA/connector/pull/92)
* Use custom connector environments and instantiate them with needed attributes (https://github.com/OCA/connector/pull/108)
* A new default implementation for the binder (https://github.com/OCA/connector/pull/76)
* Translations are now automatically synchronized from Transifex
* Mapper: add modifier to follow m2o relations with dot notation (https://github.com/OCA/connector/pull/94)
* Mapper: add 'changed_by_fields' which indicates which source fields will output data (https://github.com/OCA/connector/pull/73)
* Allow to assign a default channel on @job functions (https://github.com/OCA/connector/pull/71)
* Fix: connector-runner: manages retryable errors (https://github.com/OCA/connector/pull/87)
* Fix: connector-runner: logging error when a capacity is None (https://github.com/OCA/connector/pull/98)
* Fix: connector-runner: shows a wrong job result on retried jobs (https://github.com/OCA/connector/pull/101)
* Fix: add an index on queue_job.worker_id (https://github.com/OCA/connector/pull/89)
* Fix: Tests: common.DB is gone in 8.0 stable (https://github.com/OCA/connector/pull/79)
* Fix: connector-runner: graceful stop mechanism (https://github.com/OCA/connector/pull/69)
* Fix: connector-runner: Wrong arguments position in a log message (https://github.com/OCA/connector/pull/67)


3.1.0 (2015-05-15)
~~~~~~~~~~~~~~~~~~

* New jobs runner (details on https://github.com/OCA/connector/pull/52)
* French documentation (https://github.com/OCA/connector/pull/57)
* Add ConnectorSession.from_env() (https://github.com/OCA/connector/pull/66)
* Fix: missing indexes on jobs (https://github.com/OCA/connector/pull/65)


3.0.0 (2015-04-01)
~~~~~~~~~~~~~~~~~~

/!\ Backwards incompatible changes inside.

* Add ``openerp.api.Environment`` in ``Session``
  It is accessible in ``self.env`` in ``Session`` and all
  ``ConnectorUnit`` instances.
  Also in ``ConnectorUnit``, ``model`` returns the current (new api!) model:

  .. code-block:: python

      # On the current model
      self.model.search([])
      self.model.browse(ids)
      # on another model
      self.env['res.users'].search([])
      self.env['res.users'].browse(ids)

* Deprecate the CRUD methods in ``Session``

  .. code-block:: python

      # NO
      self.session.search('res.partner', [])
      self.session.browse('res.partner', ids)

      # YES
      self.env['res.partner'].search([])
      self.env['res.partner'].browse(ids)

* ``Environment.set_lang()`` is removed. It was modifying the context
  in place which is not possible with the new frozendict context. It
  should be done with:

  .. code-block:: python

      with self.session.change_context(lang=lang_code):
          ...

* Add an argument on the Binders methods to return a browse record

  .. code-block:: python

      binder.to_openerp(magento_id, browse=True)

* Shorten ``ConnectorUnit.get_binder_for_model`` to
  ``ConnectorUnit.binder_for``
* Shorten ``ConnectorUnit.get_connector_unit_for_model`` to
  ``ConnectorUnit.unit_for``
* Renamed ``Environment`` to ``ConnectorEnvironment`` to avoid
  confusion with ``openerp.api.Environment``
* Renamed the class attribute ``ConnectorUnit.model_name`` to
  ``ConnectorUnit.for_model_name``.
* Added ``_base_binder``, ``_base_mapper``, ``_base_backend_adapter`` in
  the synchronizers (Importer, Exporter) so it is no longer required to
  override the ``binder``, ``mapper``, ``backend_adapter`` property
  methods
* ``Session.change_context()`` now supports the same
  argument/keyword arguments semantics than
  ``openerp.model.BaseModel.with_context()``.
* Renamed ``ExportSynchronizer`` to ``Exporter``
* Renamed ``ImportSynchronizer`` to ``Importer``
* Renamed ``DeleteSynchronizer`` to ``Deleter``
* ``Session.commit`` do not commit when tests are running
* Cleaned the methods that have been deprecated in version 2.x


2.2.0 (2014-05-26)
~~~~~~~~~~~~~~~~~~

* Job arguments can now contain unicode strings (thanks to Stéphane Bidoul) lp:1288187
* List view of the jobs improved
* Jobs now support multicompany (thanks to Laurent Mignon) https://lists.launchpad.net/openerp-connector-community/msg00253.html)
* An action can be assigned to a job.  The action is called with a button on the job and could be something like open a form view or an url.

2.1.1 (2014-02-06)
~~~~~~~~~~~~~~~~~~

* A user can be blocked because he has no access to the model queue.job when a
  job has been delayed. The creation of a job is low level and should not be
  restrained by the accesses of the user. (lp:1276182)

2.1.0 (2014-01-15 - warning: breaks compatibility)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Add a new optional keyword argument 'description' to the delay() function of a
  job.  If given, the description is used as name of the queue.job record stored
  in OpenERP and displayed in the list of jobs.
* Fix: assignment of jobs to workers respect the priority of the jobs (lp:1252681)
* Pass a new parameter to listeners of 'on_record_create' ( vals:  field values
  of the new record, e.g {'field_name': field_value, ...})
* Replace the list of updated fields passed to listeners of 'on_record_write'
  by a dictionary of updated field values e.g {'field_name': field_value, ...}
* Add the possibility to use 'Modifiers' functions in the 'direct
  mappings' (details in the documentation of the Mapper class)
* When a job a delayed, the job's UUID is returned by the delay() function
* Refactoring of mappers. Much details here:
  https://code.launchpad.net/~openerp-connector-core-editors/openerp-connector/7.0-connector-mapper-refactor/+merge/194485

2.0.1 (2013-09-12)
~~~~~~~~~~~~~~~~~~

* Developers of addons do no longer need to create an AbstractModel with a _name 'name_of_the_module.installed',
  instead, they just have to call connector.connector.install_in_connector() lp:1196859
* Added a script `openerp-connector-worker` to start processes for Jobs Workers when running OpenERP is multiprocessing
* Fix: inheritance broken when an orm.Model inherit from an orm.AbstractModel. One effect was that the mail.thread features were no longer working (lp:1233355)
* Fix: do no fail to start when OpenERP has access to a not-OpenERP database (lp:1233388)


2.0.0
~~~~~

* First release


..
  Model:
  2.0.1 (date of release)
  ~~~~~~~~~~~~~~~~~~~~~~~

  * change 1
  * change 2
