import logging
from typing import TYPE_CHECKING, Any

from lxml import etree
from lxml.builder import E

from odoo import api, fields, models, tools
from odoo.exceptions import UserError
from odoo.tools import SQL, _, config, frozendict

if TYPE_CHECKING:
    from lxml.etree import _Element

_logger = logging.getLogger(__name__)

_xpath_descendant_field = etree.ETXPath("./*[descendant::field]")


class Base(models.AbstractModel):
    _inherit = "base"

    _date_name = "date"  #: field to use for default calendar view

    def _get_access_action(
        self, access_uid: int | None = None, force_website: bool = False
    ) -> dict[str, Any]:
        """Return an action to open the document. This method is meant to be
        overridden in addons that want to give specific access to the document.
        By default, it opens the formview of the document.

        :param access_uid: optional access_uid being the user that
            accesses the document. May be different from the current user as we
            may compute an access for someone else.
        :type access_uid: int | None
        :param force_website: force frontend redirection if available
            on self. Used in overrides, notably with portal / website addons.
        """
        self.ensure_one()
        return self.get_formview_action(access_uid=access_uid)

    @api.model
    def get_empty_list_help(self, help_message: str) -> str:
        """Hook method to customize the help message in empty list/kanban views.

        By default, it returns the help received as parameter.

        :param help_message: ir.actions.act_window help content
        :return: help message displayed when there is no result to display
          in a list/kanban view (by default, it returns the action help)
        """
        return help_message

    #
    # Override this method if you need a window title that depends on the context
    #
    @api.model
    def view_header_get(self, view_id: int | None, view_type: str) -> str | bool:
        return False

    @api.model
    def _get_default_form_view(self) -> _Element:
        """Generates a default single-line form view using all fields
        of the current model.

        :returns: a form view as an lxml document
        :rtype: _Element
        """
        sheet = E.sheet(string=self._description)
        main_group = E.group()
        left_group = E.group()
        right_group = E.group()
        for fname, field in self._fields.items():
            if (
                fname in models.MAGIC_COLUMNS
                or (fname == "display_name" and field.readonly)
                or (
                    field.type == "binary"
                    and not isinstance(field, fields.Image)
                    and not field.store
                )
            ):
                continue
            if field.type in ("one2many", "many2many", "text", "html"):
                # append to sheet left and right group if needed
                if len(left_group) > 0:
                    main_group.append(left_group)
                    left_group = E.group()
                if len(right_group) > 0:
                    main_group.append(right_group)
                    right_group = E.group()
                if len(main_group) > 0:
                    sheet.append(main_group)
                    main_group = E.group()
                # add an oneline group for field type 'one2many', 'many2many', 'text', 'html'
                sheet.append(E.group(E.field(name=fname)))
            elif len(left_group) > len(right_group):
                right_group.append(E.field(name=fname))
            else:
                left_group.append(E.field(name=fname))
        if len(left_group) > 0:
            main_group.append(left_group)
        if len(right_group) > 0:
            main_group.append(right_group)
        sheet.append(main_group)
        sheet.append(E.group(E.separator()))
        return E.form(sheet)

    @api.model
    def _get_default_search_view(self) -> _Element:
        """Generates a single-field search view, based on _rec_name.

        :returns: a search view as an lxml document
        :rtype: _Element
        """
        element = E.field(name=self._rec_name_fallback())
        return E.search(element, string=self._description)

    @api.model
    def _get_default_list_view(self) -> _Element:
        """Generates a single-field list view, based on _rec_name.

        :returns: a list view as an lxml document
        :rtype: _Element
        """
        element = E.field(name=self._rec_name_fallback())
        return E.list(element, string=self._description)

    @api.model
    def _get_default_pivot_view(self) -> _Element:
        """Generates an empty pivot view.

        :returns: a pivot view as an lxml document
        :rtype: _Element
        """
        return E.pivot(string=self._description)

    @api.model
    def _get_default_kanban_view(self) -> _Element:
        """Generates a single-field kanban view, based on _rec_name.

        :returns: a kanban view as an lxml document
        :rtype: _Element
        """

        field = E.field(name=self._rec_name_fallback())
        kanban_card = E.t(field, {"t-name": "card"})
        templates = E.templates(kanban_card)
        return E.kanban(templates, string=self._description)

    @api.model
    def _get_default_graph_view(self) -> _Element:
        """Generates a single-field graph view, based on _rec_name.

        :returns: a graph view as an lxml document
        :rtype: _Element
        """
        element = E.field(name=self._rec_name_fallback())
        return E.graph(element, string=self._description)

    @api.model
    def _get_default_calendar_view(self) -> _Element:
        """Generates a default calendar view by trying to infer
        calendar fields from a number of pre-set attribute names

        :returns: a calendar view
        :rtype: _Element
        """

        def set_first_of(seq: list[str], in_: dict, to: str) -> bool:
            """Sets the first value of ``seq`` also found in ``in_`` to
            the ``to`` attribute of the ``view`` being closed over.

            Returns whether it's found a suitable value (and set it on
            the attribute) or not
            """
            for item in seq:
                if item in in_ and in_[item]._description_searchable:
                    view.set(to, item)
                    return True
            return False

        view = E.calendar(string=self._description)
        view.append(E.field(name=self._rec_name_fallback()))

        if not set_first_of(
            [self._date_name, "date", "date_start", "x_date", "x_date_start"],
            self._fields,
            "date_start",
        ):
            raise UserError(_("Insufficient fields for Calendar View!"))

        set_first_of(
            ["user_id", "partner_id", "x_user_id", "x_partner_id"],
            self._fields,
            "color",
        )

        if not set_first_of(
            ["date_stop", "date_end", "x_date_stop", "x_date_end"],
            self._fields,
            "date_stop",
        ):
            if not set_first_of(
                [
                    "date_delay",
                    "planned_hours",
                    "x_date_delay",
                    "x_planned_hours",
                ],
                self._fields,
                "date_delay",
            ):
                raise UserError(
                    _(
                        "Insufficient fields to generate a Calendar View for %s, missing a date_stop or a date_delay",
                        self._name,
                    )
                )

        return view

    @api.model
    @api.readonly
    def get_views(
        self,
        views: list[list[int | str]],
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Returns the fields_views of given views, along with the fields of
        the current model, and optionally its filters for the given action.

        The return of the method can only depend on the requested view types,
        access rights (views or other records), view access rules, options,
        context lang and TYPE_view_ref (other context values cannot be used).

        Python expressions contained in views or representing domains (on
        python fields) will be evaluated by the client with all the context
        values as well as the record values it has.

        :param views: list of [view_id, view_type]
        :param options: a dict optional boolean flags, set to enable:

            ``toolbar``
                includes contextual actions when loading fields_views
            ``load_filters``
                returns the model's filters
            ``action_id``
                id of the action to get the filters, otherwise loads the global
                filters or the model

        :type options: dict[str, Any] | None
        :return: dictionary with fields_views, fields and optionally filters
        """
        options = options or {}
        result = {}

        result["views"] = {
            v_type: self.get_view(v_id, v_type, **options) for [v_id, v_type] in views
        }

        models = {}
        for view in result["views"].values():
            for model, model_fields in view.pop("models").items():
                models.setdefault(model, set()).update(model_fields)

        result["models"] = {}

        for model, model_fields in models.items():
            result["models"][model] = {
                "fields": self.env[model].fields_get(
                    allfields=model_fields,
                    attributes=self._get_view_field_attributes(),
                )
            }

        # Add related action information if asked
        if options.get("toolbar"):
            for view in result["views"].values():
                view["toolbar"] = {}

            bindings = self.env["ir.actions.actions"].get_bindings(self._name)
            for action_type, key in (("report", "print"), ("action", "action")):
                for action in bindings.get(action_type, []):
                    view_types = (
                        action["binding_view_types"].split(",")
                        if action.get("binding_view_types")
                        else result["views"].keys()
                    )
                    for view_type in view_types:
                        if view_type in result["views"]:
                            result["views"][view_type]["toolbar"].setdefault(
                                key, []
                            ).append(action)

        if options.get("load_filters") and "search" in result["views"]:
            result["views"]["search"]["filters"] = self.env["ir.filters"].get_filters(
                self._name,
                options.get("action_id"),
                options.get("embedded_action_id"),
                options.get("embedded_parent_res_id"),
            )

        return result

    @api.model
    def _get_view(
        self,
        view_id: int | None = None,
        view_type: str = "form",
        **options: Any,
    ) -> tuple[_Element, Any]:
        """
        Get the model view combined architecture (the view along all its
        inheriting views).

        :param view_id: id of the view or None
        :type view_id: int | None
        :param str view_type: type of the view to return if view_id is None,
            one of ``'form'``, ``'list'``, ...
        :param options: options to return additional features

            :param bool mobile: true if the web client is currently using the
                responsive mobile view (to use kanban views instead of list
                views for x2many fields)

        :return: architecture of the view as an etree node, and the browse
            record of the view used
        :rtype: tuple[_Element, Any]
        :raise AttributeError: if no view exists for that model, and no method
            ``_get_default_<view_type>_view`` exists for the view type
        """
        IrUiView = self.env["ir.ui.view"].sudo()

        # try to find a view_id if none provided
        if not view_id:
            # <view_type>_view_ref in context can be used to override the default view
            view_ref_key = view_type + "_view_ref"
            view_ref = self.env.context.get(view_ref_key)
            if view_ref:
                if "." in view_ref:
                    module, view_ref = view_ref.split(".", 1)

                    sql = SQL(
                        "SELECT res_id FROM ir_model_data WHERE model='ir.ui.view' AND module=%s AND name=%s",
                        module,
                        view_ref,
                    )
                    if view_ref_res := self.env.execute_query(sql):
                        [[view_id]] = view_ref_res
                else:
                    _logger.warning(
                        "%r requires a fully-qualified external id (got: %r for model %s). "
                        "Please use the complete `module.view_id` form instead.",
                        view_ref_key,
                        view_ref,
                        self._name,
                    )

            if not view_id:
                # otherwise try to find the lowest priority matching ir.ui.view
                view_id = IrUiView.default_view(self._name, view_type)

        if view_id:
            # read the view with inherited views applied
            view = IrUiView.browse(view_id)
            arch = view._get_combined_arch()
        else:
            # fallback on default views methods if no ir.ui.view could be found
            view = IrUiView.browse()
            method = getattr(self, f"_get_default_{view_type}_view", None)
            if method is None:
                raise UserError(
                    _("No default view of type '%s' could be found!", view_type)
                )
            arch = method()
        return arch, view

    def _get_view_postprocessed(
        self, view: Any, arch: _Element, **options: Any
    ) -> tuple[str, dict[str, set[str]]]:
        """
        Get the post-processed view architecture and the corresponding fields.

        This method uses the view's ``postprocess_and_fields`` function to process
        the view architecture. It applies access control rules, field modifiers,
        and tag-specific logic. It also automatically embeds subviews for
        ``one2many`` and ``many2many`` fields when required, and collects all
        fields used across the view and its subviews.

        :param view: an ``ir.ui.view`` record
        :param arch: the view architecture as a string
        :param options: bool options to return additional features:
                        ``mobile`` (bool): true if the web client is currently using
                        the responsive mobile view (to use kanban views instead of
                        list views for x2many fields)
        :return: a tuple containing:
                - the post-processed view architecture as a string
                - a dictionary of models and the fields used in the view
        :rtype: tuple[str, dict[str, set[str]]]
        """
        return view.postprocess_and_fields(arch, model=self._name, **options)

    @api.model
    def _get_view_cache_key(
        self,
        view_id: int | None = None,
        view_type: str = "form",
        **options: Any,
    ) -> tuple:
        """Get the key to use for caching `_get_view_cache`.

        This method is meant to be overridden by models needing additional keys.

        :param view_id: id of the view or None
        :type view_id: int | None
        :param str view_type: type of the view to return if view_id is None,
            one of ``'form'``, ``'list'``, ...
        :param options: options to return additional features

            :param bool mobile: true if the web client is currently using the
                responsive mobile view (to use kanban views instead of list
                views for x2many fields)

        :return: a cache key
        :rtype: tuple
        """
        return (
            view_id,
            view_type,
            options.get("mobile"),
            self.env.lang,
        ) + tuple(
            (key, value)
            for key, value in self.env.context.items()
            if key.endswith("_view_ref")
        )

    @api.model
    @tools.conditional(
        "xml" not in config["dev_mode"],
        tools.ormcache(
            "self._get_view_cache_key(view_id, view_type, **options)",
            cache="templates",
        ),
    )
    def _get_view_cache(
        self,
        view_id: int | None = None,
        view_type: str = "form",
        **options: Any,
    ) -> frozendict:
        """Get the view information ready to be cached

        The cached view includes the postprocessed view, including inherited
        views, for all groups. The blocks restricted to groups must therefore
        be removed after calling this method for users not part of the given
        groups.

        :param view_id: id of the view or None
        :type view_id: int | None
        :param str view_type: type of the view to return if view_id is None,
            one of ``'form'``, ``'list'``, ...
        :param options: options to return additional features

            :param bool mobile: true if the web client is currently using the
                responsive mobile view (to use kanban views instead of list
                views for x2many fields)

        :return: a dictionary including

            - string arch: the architecture of the view (including inherited views, postprocessed, for all groups)
            - int id: the view id
            - string model: the view model
            - dict models: the fields of the models used in the view (including sub-views)

        :rtype: frozendict
        """
        # Get the view arch and all other attributes describing the composition of the view
        arch, view = self._get_view(view_id, view_type, **options)

        # Apply post processing, groups and modifiers etc...
        arch, models = self._get_view_postprocessed(view, arch, **options)
        models = self._get_view_fields(view_type or view.type, models)
        result = {
            "arch": arch,
            # TODO: only `web_studio` seems to require this. I guess this is acceptable to keep it.
            "id": view.id,
            # TODO: only `web_studio` seems to require this. But this one on the other hand should be eliminated:
            # you just called `get_views` for that model, so obviously the web client already knows the model.
            "model": self._name,
            # Set a frozendict and tuple for the field list to make sure the value in cache cannot be updated.
            "models": frozendict(
                {model: tuple(fields) for model, fields in models.items()}
            ),
        }

        return frozendict(result)

    @api.model
    def get_view(
        self,
        view_id: int | None = None,
        view_type: str = "form",
        **options: Any,
    ) -> dict[str, Any]:
        """get_view([view_id | view_type='form'])

        Get the detailed composition of the requested view like model, view
        architecture.

        The return of the method can only depend on the requested view types,
        access rights (views or other records), view access rules, options,
        context lang and TYPE_view_ref (other context values cannot be used).

        :param view_id: id of the view or None
        :type view_id: int | None
        :param str view_type: type of the view to return if view_id is None,
            one of ``'form'``, ``'list'``, ...
        :param options: options to return additional features

            :param bool mobile: true if the web client is currently using the
                responsive mobile view (to use kanban views instead of list
                views for x2many fields)

        :return: composition of the requested view (including inherited views
            and extensions)
        :rtype: dict[str, Any]
        :raise AttributeError:

            * if the inherited view has unknown position to work with other
              than 'before', 'after', 'inside', 'replace'
            * if some tag other than 'position' is found in parent view
        """
        self.browse().check_access("read")

        result = dict(self._get_view_cache(view_id, view_type, **options))

        node = etree.fromstring(result["arch"])
        node = self.env["ir.ui.view"]._postprocess_access_rights(node)
        node = self.env["ir.ui.view"]._postprocess_debug(node)
        result["arch"] = etree.tostring(node, encoding="unicode").replace("\t", "")

        return result

    @api.model
    def _get_view_fields(
        self, view_type: str, models: dict[str, Any]
    ) -> dict[str, Any]:
        """Returns the field names required by the web client to load the views according to the view type.

        The method is meant to be overridden by modules extending web client features and requiring additional
        fields.

        :param str view_type: type of the view
        :param dict[str, Any] models: dict holding the models and fields used in the view architecture.
        :return: dict holding the models and field required by the web client given the view type.
        :rtype: dict[str, Any]
        """
        match view_type:
            case "kanban" | "list" | "form":
                for model, model_fields in models.items():
                    model_fields.add("id")
                    if "write_date" in self.env[model]._fields:
                        model_fields.add("write_date")
            case "search":
                models[self._name] = list(self._fields.keys())
            case "graph":
                models[self._name].update(
                    fname
                    for fname, field in self._fields.items()
                    if field.type in ("integer", "float", "monetary")
                )
            case "pivot":
                models[self._name].update(
                    fname
                    for fname, field in self._fields.items()
                    if field._description_groupable(self.env)
                )
        return models

    @api.model
    def _get_view_field_attributes(self) -> list[str]:
        """Returns the field attributes required by the web client to load the views.

        The method is meant to be overridden by modules extending web client features and requiring additional
        field attributes.

        :return: string list of field attribute names
        :rtype: list[str]
        """
        return [
            "change_default",
            "context",
            "currency_field",
            "definition_record",
            "definition_record_field",
            "digits",
            "min_display_digits",
            "domain",
            "aggregator",
            "groups",
            "help",
            "model_field",
            "name",
            "readonly",
            "related",
            "relation",
            "relation_field",
            "required",
            "searchable",
            "selection",
            "size",
            "sortable",
            "store",
            "string",
            "translate",
            "trim",
            "type",
            "groupable",
            "falsy_value_label",
        ]

    @api.readonly
    def get_formview_id(self, access_uid: int | None = None) -> int | bool:
        """Return a view id to open the document ``self`` with. This method is
        meant to be overridden in addons that want to give specific view ids
        for example.

        Optional access_uid holds the user that would access the form view
        id different from the current environment user.
        """
        return False

    @api.readonly
    def get_formview_action(self, access_uid: int | None = None) -> dict[str, Any]:
        """Return an action to open the document ``self``. This method is meant
            to be overridden in addons that want to give specific view ids for
            example.

        An optional access_uid holds the user that will access the document
        that could be different from the current user."""
        view_id = self.sudo().get_formview_id(access_uid=access_uid)
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "views": [(view_id, "form")],
            "target": "current",
            "res_id": self.id,
            "context": dict(self.env.context),
        }

    def _get_records_action(self, **kwargs: Any) -> dict[str, Any]:
        """Return an action to open given records.
        If there's more than one record, it will be a List, otherwise it's a Form.
        Given keyword arguments will overwrite default ones."""
        match self.ids:  # `self.ids` will silently filter out new records (`NewId`s)
            case []:
                length_dependent = {"views": [(False, "form")]}
            case [res_id]:
                length_dependent = {
                    "views": [(False, "form")],
                    "res_id": res_id,
                }
            case ids:
                length_dependent = {
                    "views": [(False, "list"), (False, "form")],
                    "domain": [("id", "in", ids)],
                }
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "target": "current",
            "context": dict(self.env.context),
            **length_dependent,
            **kwargs,
        }

    @api.model
    def _onchange_spec(
        self, view_info: dict[str, Any] | None = None
    ) -> dict[str, str | None]:
        """Return the onchange spec from a view description; if not given, the
        result of ``self.get_view()`` is used.
        """
        result = {}

        # for traversing the XML arch and populating result
        def process(node: _Element, info: dict[str, Any] | None, prefix: str) -> None:
            if node.tag == "field":
                name = node.attrib["name"]
                names = f"{prefix}.{name}" if prefix else name
                if not result.get(names):
                    result[names] = node.attrib.get("on_change")
                # traverse the subviews included in relational fields
                for child_view in _xpath_descendant_field(node):
                    process(child_view, None, names)
            else:
                for child in node:
                    process(child, info, prefix)

        if view_info is None:
            view_info = self.get_view()
        process(etree.fromstring(view_info["arch"]), view_info, "")
        return result

    @api.model
    def _get_fields_spec(
        self, view_info: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Return the fields specification from a view description; if not
        given, the result of ``self.get_view()`` is used.
        """

        def fill_spec(node: _Element, model: Any, fields_spec: dict[str, Any]) -> None:
            if node.tag == "field":
                field_name = node.attrib["name"]
                field_spec = fields_spec.setdefault(field_name, {})
                field = model._fields.get(field_name)
                if field is not None:
                    sub_fields_spec = {}
                    if field.type == "many2one":
                        sub_fields_spec.setdefault("display_name", {})
                    if field.relational:
                        comodel = model.env[field.comodel_name]
                        for child in node:
                            fill_spec(child, comodel, sub_fields_spec)
                    if field.type == "one2many":
                        sub_fields_spec.pop(field.inverse_name, None)
                    if sub_fields_spec:
                        field_spec.setdefault("fields", {}).update(sub_fields_spec)
            else:
                for child in node:
                    fill_spec(child, model, fields_spec)

        if view_info is None:
            view_info = self.get_view()

        result = {}
        fill_spec(etree.fromstring(view_info["arch"]), self, result)
        return result
