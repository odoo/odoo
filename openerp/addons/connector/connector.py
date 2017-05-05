# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2012 Camptocamp SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import hashlib
import logging
import struct

from openerp import models, fields

from .exception import RetryableJobError

_logger = logging.getLogger(__name__)


def _get_openerp_module_name(module_path):
    """ Extract the name of the OpenERP module from the path of the
    Python module.

    Taken from OpenERP server: ``openerp.models.MetaModel``

    The (OpenERP) module name can be in the ``openerp.addons`` namespace
    or not. For instance module ``sale`` can be imported as
    ``openerp.addons.sale`` (the good way) or ``sale`` (for backward
    compatibility).
    """
    module_parts = module_path.split('.')
    if len(module_parts) > 2 and module_parts[:2] == ['openerp', 'addons']:
        module_name = module_parts[2]
    else:
        module_name = module_parts[0]
    return module_name


def is_module_installed(env, module_name):
    """ Check if an Odoo addon is installed.

    :param module_name: name of the addon
    """
    # the registry maintains a set of fully loaded modules so we can
    # lookup for our module there
    return module_name in env.registry._init_modules


def get_openerp_module(cls_or_func):
    """ For a top level function or class, returns the
    name of the OpenERP module where it lives.

    So we will be able to filter them according to the modules
    installation state.
    """
    return _get_openerp_module_name(cls_or_func.__module__)


class MetaConnectorUnit(type):
    """ Metaclass for ConnectorUnit.

    Keeps a ``_module`` attribute on the classes, the same way OpenERP does
    it for the Model classes. It is then used to filter them according to
    the state of the module (installed or not).
    """

    @property
    def for_model_names(cls):
        """ Returns the list of models on which a
        :class:`~connector.connector.ConnectorUnit` is usable

        It is used in :meth:`~connector.connector.ConnectorUnit.match` when
        we search the correct ``ConnectorUnit`` for a model.

        """
        if cls._model_name is None:
            raise NotImplementedError("no _model_name for %s" % cls)
        model_name = cls._model_name
        if not hasattr(model_name, '__iter__'):
            model_name = [model_name]
        return model_name

    def __init__(cls, name, bases, attrs):
        super(MetaConnectorUnit, cls).__init__(name, bases, attrs)
        cls._openerp_module_ = get_openerp_module(cls)


class ConnectorUnit(object):
    """Abstract class for each piece of the connector:

    Examples:
        * :py:class:`connector.connector.Binder`
        * :py:class:`connector.unit.mapper.Mapper`
        * :py:class:`connector.unit.synchronizer.Synchronizer`
        * :py:class:`connector.unit.backend_adapter.BackendAdapter`

    Or basically any class intended to be registered in a
    :py:class:`~connector.backend.Backend`.
    """

    __metaclass__ = MetaConnectorUnit

    _model_name = None  # to be defined in sub-classes

    def __init__(self, connector_env):
        """

        :param connector_env: current environment (backend, session, ...)
        :type connector_env: :class:`connector.connector.ConnectorEnvironment`
        """
        super(ConnectorUnit, self).__init__()
        self.connector_env = connector_env
        self.backend = self.connector_env.backend
        self.backend_record = self.connector_env.backend_record
        self.session = self.connector_env.session

    @classmethod
    def match(cls, session, model):
        """ Returns True if the current class correspond to the
        searched model.

        :param session: current session
        :type session: :py:class:`connector.session.ConnectorSession`
        :param model: model to match
        :type model: str or :py:class:`openerp.models.Model`
        """
        # filter out the ConnectorUnit from modules
        # not installed in the current DB
        if hasattr(model, '_name'):  # Model instance
            model_name = model._name
        else:
            model_name = model  # str
        return model_name in cls.for_model_names

    @property
    def env(self):
        """ Returns the openerp.api.environment """
        return self.session.env

    @property
    def model(self):
        return self.connector_env.model

    @property
    def localcontext(self):
        """ It is there for compatibility.

        :func:`openerp.tools.translate._` searches for this attribute
        in the classes do be able to translate the strings.

        There is no reason to use this attribute for other purposes.
        """
        return self.session.context

    def unit_for(self, connector_unit_class, model=None):
        """ According to the current
        :py:class:`~connector.connector.ConnectorEnvironment`,
        search and returns an instance of the
        :py:class:`~connector.connector.ConnectorUnit` for the current
        model and being a class or subclass of ``connector_unit_class``.

        If a different ``model`` is given, a new ConnectorEnvironment is built
        for this model. The class used for creating the new environment is
        the same class as in `self.connector_env` which must be
        :py:class:`~connector.connector.ConnectorEnvironment` or a subclass.

        :param connector_unit_class: ``ConnectorUnit`` to search
                                     (class or subclass)
        :type connector_unit_class: :py:class:`connector.\
                                               connector.ConnectorUnit`
        :param model: to give if the ``ConnectorUnit`` is for another
                      model than the current one
        :type model: str
        """
        if model is None or model == self.model._name:
            env = self.connector_env
        else:
            env = self.connector_env.create_environment(
                self.backend_record,
                self.session, model,
                connector_env=self.connector_env)

        return env.get_connector_unit(connector_unit_class)

    def binder_for(self, model=None):
        """ Returns an new instance of the correct ``Binder`` for
        a model """
        return self.unit_for(Binder, model)

    def advisory_lock_or_retry(self, lock, retry_seconds=1):
        """ Acquire a Postgres transactional advisory lock or retry job

        When the lock cannot be acquired, it raises a
        ``RetryableJobError`` so the job is retried after n
        ``retry_seconds``.

        Usage example:

        ::

            lock_name = 'import_record({}, {}, {}, {})'.format(
                self.backend_record._name,
                self.backend_record.id,
                self.model._name,
                self.external_id,
            )
            self.advisory_lock_or_retry(lock_name, retry_seconds=2)

        See :func:``openerp.addons.connector.connector.pg_try_advisory_lock``
        for details.

        :param lock: The lock name. Can be anything convertible to a
           string.  It needs to represent what should not be synchronized
           concurrently, usually the string will contain at least: the
           action, the backend type, the backend id, the model name, the
           external id
        :param retry_seconds: number of seconds after which a job should
           be retried when the lock cannot be acquired.
        """
        if not pg_try_advisory_lock(self.env, lock):
            raise RetryableJobError('Could not acquire advisory lock',
                                    seconds=retry_seconds,
                                    ignore_retry=True)


class ConnectorEnvironment(object):
    """ Environment used by the different units for the synchronization.

    .. attribute:: backend

        Current backend we are working with.
        Obtained with ``backend_record.get_backend()``.

        Instance of: :py:class:`connector.backend.Backend`

    .. attribute:: backend_record

        Browsable record of the backend. The backend is inherited
        from the model ``connector.backend`` and have at least a
        ``type`` and a ``version``.

    .. attribute:: session

        Current session we are working in. It contains the OpenERP
        cr, uid and context.

    .. attribute:: model_name

        Name of the OpenERP model to work with.

    .. attribute:: _propagate_kwargs

        List of attributes that must be used by
        :py:meth:`connector.connector.ConnectorEnvironment.create_environment`
        when a new connector environment is instantiated.
    """

    _propagate_kwargs = []

    def __init__(self, backend_record, session, model_name):
        """

        :param backend_record: browse record of the backend
        :type backend_record: :py:class:`openerp.models.Model`
        :param session: current session (cr, uid, context)
        :type session: :py:class:`connector.session.ConnectorSession`
        :param model_name: name of the model
        :type model_name: str
        """
        self.backend_record = backend_record
        backend = backend_record.get_backend()
        self.backend = backend
        self.session = session
        self.model_name = model_name

    @property
    def model(self):
        return self.env[self.model_name]

    @property
    def pool(self):
        return self.session.pool

    @property
    def env(self):
        return self.session.env

    def get_connector_unit(self, base_class):
        """ Searches and returns an instance of the
        :py:class:`~connector.connector.ConnectorUnit` for the current
        model and being a class or subclass of ``base_class``.

        The returned instance is built with ``self`` for its environment.

        :param base_class: ``ConnectorUnit`` to search (class or subclass)
        :type base_class: :py:class:`connector.connector.ConnectorUnit`
        """
        return self.backend.get_class(base_class, self.session,
                                      self.model_name)(self)

    @classmethod
    def create_environment(cls, backend_record, session, model,
                           connector_env=None):
        """ Create a new environment ConnectorEnvironment.

        :param backend_record: browse record of the backend
        :type backend_record: :py:class:`openerp.models.Model`
        :param session: current session (cr, uid, context)
        :type session: :py:class:`connector.session.ConnectorSession`
        :param model_name: name of the model
        :type model_name: str
        :param connector_env: an existing environment from which the kwargs
                              will be propagated to the new one
        :type connector_env:
            :py:class:`connector.connector.ConnectorEnvironment`
        """
        kwargs = {}
        if connector_env:
            kwargs = {key: getattr(connector_env, key)
                      for key in connector_env._propagate_kwargs}
        if kwargs:
            return cls(backend_record, session, model, **kwargs)
        else:
            return cls(backend_record, session, model)


class Binder(ConnectorUnit):
    """ For one record of a model, capable to find an external or
    internal id, or create the binding (link) between them

    This is a default implementation that can be inherited or reimplemented
    in the connectors.

    This implementation assumes that binding models are ``_inherits`` of
    the models they are binding.
    """

    _model_name = None  # define in sub-classes
    _external_field = 'external_id'  # override in sub-classes
    _backend_field = 'backend_id'  # override in sub-classes
    _openerp_field = 'openerp_id'  # override in sub-classes
    _sync_date_field = 'sync_date'  # override in sub-classes

    def to_openerp(self, external_id, unwrap=False):
        """ Give the OpenERP ID for an external ID

        :param external_id: external ID for which we want
                            the OpenERP ID
        :param unwrap: if True, returns the normal record
                       else return the binding record
        :return: a recordset, depending on the value of unwrap,
                 or an empty recordset if the external_id is not mapped
        :rtype: recordset
        """
        bindings = self.model.with_context(active_test=False).search(
            [(self._external_field, '=', str(external_id)),
             (self._backend_field, '=', self.backend_record.id)]
        )
        if not bindings:
            return self.model.browse()
        bindings.ensure_one()
        if unwrap:
            bindings = getattr(bindings, self._openerp_field)
        return bindings

    def to_backend(self, binding_id, wrap=False):
        """ Give the external ID for an OpenERP binding ID

        :param binding_id: OpenERP binding ID for which we want the backend id
        :param wrap: if False, binding_id is the ID of the binding,
                     if True, binding_id is the ID of the normal record, the
                     method will search the corresponding binding and returns
                     the backend id of the binding
        :return: external ID of the record
        """
        record = self.model.browse()
        if isinstance(binding_id, models.BaseModel):
            binding_id.ensure_one()
            record = binding_id
            binding_id = binding_id.id
        if wrap:
            binding = self.model.with_context(active_test=False).search(
                [(self._openerp_field, '=', binding_id),
                 (self._backend_field, '=', self.backend_record.id),
                 ]
            )
            if not binding:
                return None
            binding.ensure_one()
            return getattr(binding, self._external_field)
        if not record:
            record = self.model.browse(binding_id)
        assert record
        return getattr(record, self._external_field)

    def bind(self, external_id, binding_id):
        """ Create the link between an external ID and an OpenERP ID

        :param external_id: external id to bind
        :param binding_id: OpenERP ID to bind
        :type binding_id: int
        """
        # Prevent False, None, or "", but not 0
        assert (external_id or external_id == 0) and binding_id, (
            "external_id or binding_id missing, "
            "got: %s, %s" % (external_id, binding_id)
        )
        # avoid to trigger the export when we modify the `external_id`
        now_fmt = fields.Datetime.now()
        if not isinstance(binding_id, models.BaseModel):
            binding_id = self.model.browse(binding_id)
        binding_id.with_context(connector_no_export=True).write(
            {self._external_field: str(external_id),
             self._sync_date_field: now_fmt,
             })

    def unwrap_binding(self, binding_id, browse=False):
        """ For a binding record, gives the normal record.

        Example: when called with a ``magento.product.product`` id,
        it will return the corresponding ``product.product`` id.

        :param browse: when True, returns a browse_record instance
                       rather than an ID
        """
        if isinstance(binding_id, models.BaseModel):
            binding = binding_id
        else:
            binding = self.model.browse(binding_id)

        openerp_record = getattr(binding, self._openerp_field)
        if browse:
            return openerp_record
        return openerp_record.id

    def unwrap_model(self):
        """ For a binding model, gives the normal model.

        Example: when called on a binder for ``magento.product.product``,
        it will return ``product.product``.
        """
        try:
            column = self.model._fields[self._openerp_field]
        except KeyError:
            raise ValueError(
                'Cannot unwrap model %s, because it has no %s fields'
                % (self.model._name, self._openerp_field))
        return column.comodel_name


def pg_try_advisory_lock(env, lock):
    """ Try to acquire a Postgres transactional advisory lock.

    The function tries to acquire a lock, returns a boolean indicating
    if it could be obtained or not. An acquired lock is released at the
    end of the transaction.

    A typical use is to acquire a lock at the beginning of an importer
    to prevent 2 jobs to do the same import at the same time. Since the
    record doesn't exist yet, we can't put a lock on a record, so we put
    an advisory lock.

    Example:
     - Job 1 imports Partner A
     - Job 2 imports Partner B
     - Partner A has a category X which happens not to exist yet
     - Partner B has a category X which happens not to exist yet
     - Job 1 import category X as a dependency
     - Job 2 import category X as a dependency

    Since both jobs are executed concurrently, they both create a record
    for category X so we have duplicated records.  With this lock:

     - Job 1 imports Partner A, it acquires a lock for this partner
     - Job 2 imports Partner B, it acquires a lock for this partner
     - Partner A has a category X which happens not to exist yet
     - Partner B has a category X which happens not to exist yet
     - Job 1 import category X as a dependency, it acquires a lock for
       this category
     - Job 2 import category X as a dependency, try to acquire a lock
       but can't, Job 2 is retried later, and when it is retried, it
       sees the category X created by Job 1.

    The lock is acquired until the end of the transaction.

    Usage example:

    ::

        lock_name = 'import_record({}, {}, {}, {})'.format(
            self.backend_record._name,
            self.backend_record.id,
            self.model._name,
            self.external_id,
        )
        if pg_try_advisory_lock(lock_name):
            # do sync
        else:
            raise RetryableJobError('Could not acquire advisory lock',
                                    seconds=2,
                                    ignore_retry=True)

    :param env: the Odoo Environment
    :param lock: The lock name. Can be anything convertible to a
       string.  It needs to represents what should not be synchronized
       concurrently so usually the string will contain at least: the
       action, the backend type, the backend id, the model name, the
       external id
    :return True/False whether lock was acquired.
    """
    hasher = hashlib.sha1()
    hasher.update('{}'.format(lock))
    # pg_lock accepts an int8 so we build an hash composed with
    # contextual information and we throw away some bits
    int_lock = struct.unpack('q', hasher.digest()[:8])

    env.cr.execute('SELECT pg_try_advisory_xact_lock(%s);', (int_lock,))
    acquired = env.cr.fetchone()[0]
    return acquired
