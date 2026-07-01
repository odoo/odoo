# Copyright 2017 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

"""
Events Internals
================

Core classes for the events system.


"""


from odoo.addons.component.core import WorkContext


class EventWorkContext(WorkContext):
    """Work context used by the Events internals

    Should not be used outside of the events internals.
    The work context to use generally is
    :class:`odoo.addons.component.core.WorkContext` or your own
    subclass.

    The events are a special kind of components because they are
    not attached to any collection (they can but not the main use case).

    So the work context must not need to have a collection, but when
    it has no collection, it must at least have an 'env'.

    When no collection is provided, the methods to get the Components
    cannot be used, but :meth:`work_on` can be used to switch back to
    a :class:`odoo.addons.component.core.WorkContext` with collection.
    This is needed when one want to get a component for a collection
    from inside an event listener.

    """

    def __init__(
        self,
        model_name=None,
        collection=None,
        env=None,
        components_registry=None,
        **kwargs
    ):
        if not (collection is not None or env):
            raise ValueError("collection or env is required")
        if collection and env:
            # when a collection is used, the env will be the one of
            # the collection
            raise ValueError("collection and env cannot both be provided")

        self.env = env
        super(EventWorkContext, self).__init__(
            model_name=model_name,
            collection=collection,
            components_registry=components_registry,
            **kwargs
        )
        if self._env:
            self._propagate_kwargs.remove("collection")
            self._propagate_kwargs.append("env")

    @property
    def env(self):
        """Return the current Odoo env"""
        if self._env:
            return self._env
        return super(EventWorkContext, self).env

    @env.setter
    def env(self, value):
        self._env = value

    @property
    def collection(self):
        """Return the current Odoo env"""
        if self._collection is not None:
            return self._collection
        raise ValueError("No collection, it is optional for EventWorkContext")

    @collection.setter
    def collection(self, value):
        self._collection = value

    def work_on(self, model_name=None, collection=None):
        """Create a new work context for another model keeping attributes

        Used when one need to lookup components for another model.

        Used on an EventWorkContext, it switch back to a normal
        WorkContext. It means we are inside an event listener, and
        we want to get a component. We need to set a collection
        to be able to get components.
        """
        if self._collection is None and collection is None:
            raise ValueError("you must provide a collection to work with")
        if collection is not None:
            if self.env is not collection.env:
                raise ValueError(
                    "the Odoo env of the collection must be "
                    "the same than the current one"
                )
        kwargs = {
            attr_name: getattr(self, attr_name) for attr_name in self._propagate_kwargs
        }
        kwargs.pop("env", None)
        if collection is not None:
            kwargs["collection"] = collection
        if model_name is not None:
            kwargs["model_name"] = model_name
        return WorkContext(**kwargs)

    def component_by_name(self, name, model_name=None):
        if self._collection is not None:
            # switch to a normal WorkContext
            work = self.work_on(collection=self._collection, model_name=model_name)
        else:
            raise TypeError(
                "Can't be used on an EventWorkContext without collection. "
                "The collection must be known to find components.\n"
                "Hint: you can set the collection and get a component with:\n"
                ">>> work.work_on(collection=self.env[...].browse(...))\n"
                ">>> work.component_by_name(name, model_name=model_name)"
            )
        return work.component_by_name(name, model_name=model_name)

    def component(self, usage=None, model_name=None):
        if self._collection is not None:
            # switch to a normal WorkContext
            work = self.work_on(collection=self._collection, model_name=model_name)
        else:
            raise TypeError(
                "Can't be used on an EventWorkContext without collection. "
                "The collection must be known to find components.\n"
                "Hint: you can set the collection and get a component with:\n"
                ">>> work.work_on(collection=self.env[...].browse(...))\n"
                ">>> work.component(usage=usage, model_name=model_name)"
            )
        return work.component(usage=usage, model_name=model_name)

    def many_components(self, usage=None, model_name=None):
        if self._collection is not None:
            # switch to a normal WorkContext
            work = self.work_on(collection=self._collection, model_name=model_name)
        else:
            raise TypeError(
                "Can't be used on an EventWorkContext without collection. "
                "The collection must be known to find components.\n"
                "Hint: you can set the collection and get a component with:\n"
                ">>> work.work_on(collection=self.env[...].browse(...))\n"
                ">>> work.many_components(usage=usage, model_name=model_name)"
            )
        return work.component(usage=usage, model_name=model_name)

    def __str__(self):
        return "EventWorkContext({},{})".format(
            repr(self._env or self._collection), self.model_name
        )
