import logging
import re
from ast import literal_eval
from typing import Any, Self

from odoo import _, api, models
from odoo.api import ValuesType
from odoo.exceptions import AccessError, RedirectWarning, UserError
from odoo.libs.debug_log import DebugLog

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

SETTINGS_CLASSIFIED_CACHE_KEY = "res_config_settings_classified_fields"


class ResConfig(models.TransientModel):
    _name = "res.config"
    _description = "Config"

    def start(self) -> dict[str, str]:
        return self._next_todo_action()

    def _next_todo_action(self) -> dict[str, str]:
        return {
            "type": "ir.actions.client",
            "tag": "reload",
        }

    def execute(self) -> dict[str, Any] | None:
        msg = "Configuration items need to implement execute"
        raise NotImplementedError(msg)

    def cancel(self) -> dict[str, Any] | None:
        pass

    def action_next(self) -> dict[str, Any] | None:
        return self.execute() or self._next_todo_action()

    def action_skip(self) -> dict[str, Any] | None:
        return self.cancel() or self._next_todo_action()

    def action_cancel(self) -> dict[str, Any] | None:
        return self.cancel() or self._next_todo_action()


class ResConfigSettings(models.TransientModel):
    _name = "res.config.settings"
    _description = "Config Settings"

    def _is_valid_field_parameter(self, field: Any, name: str) -> bool:
        return (
            name in ("default_model", "config_parameter")
            or (
                field.type in ("boolean", "selection")
                and name in ("group", "implied_group")
            )
            or super()._is_valid_field_parameter(field, name)
        )

    def copy(self, default: ValuesType | None = None) -> Self:
        _debug.logic("settings_copy_refused", model=self._name)
        raise UserError(_("Cannot duplicate configuration!"))

    @api.model
    def _install_modules(self, modules: Any) -> Any:
        result = None

        to_install_modules = modules.filtered(
            lambda module: module.state == "uninstalled"
        )
        _debug.pipeline(
            "settings_install_modules",
            requested=modules.mapped("name"),
            to_install=to_install_modules.mapped("name"),
        )
        if to_install_modules:
            result = to_install_modules.button_immediate_install()

        return result

    @api.model
    def _get_fields_classified(self, fnames: Any = None) -> dict[str, Any]:
        IrModule = self.env["ir.module.module"]
        IrModelData = self.env["ir.model.data"]
        Groups = self.env["res.groups"]

        def ref(xml_id):
            res_model, res_id = IrModelData._xmlid_to_res_model_res_id(
                xml_id, raise_if_not_found=True
            )
            return self.env[res_model].browse(res_id)

        if fnames is None:
            fnames = self._fields.keys()

        defaults, groups, configs, others = [], [], [], []
        module_recs = []
        for name in fnames:
            field = self._fields[name]
            if name.startswith("default_"):
                if not hasattr(field, "default_model"):
                    raise TypeError(f"Field {field} without attribute 'default_model'")
                defaults.append(
                    (name, field.default_model, name.removeprefix("default_"))
                )
            elif name.startswith("group_"):
                if field.type not in ("boolean", "selection"):
                    raise TypeError(
                        f"Field {field} must have type 'boolean' or 'selection'"
                    )
                if not hasattr(field, "implied_group"):
                    raise TypeError(f"Field {field} without attribute 'implied_group'")
                field_group_xmlids = getattr(field, "group", "base.group_user").split(
                    ","
                )
                field_groups = Groups.concat(*(ref(it) for it in field_group_xmlids))
                groups.append((name, field_groups, ref(field.implied_group)))
            elif name.startswith("module_"):
                if field.type != "boolean":
                    raise TypeError(f"Field {field} must have type 'boolean'")
                module_recs.append(IrModule._get(name.removeprefix("module_")))
            elif hasattr(field, "config_parameter") and field.config_parameter:
                if field.type not in (
                    "boolean",
                    "integer",
                    "float",
                    "char",
                    "selection",
                    "many2one",
                    "datetime",
                ):
                    raise TypeError(
                        "Field %s must have type 'boolean', 'integer', 'float', 'char', 'selection', 'many2one' or 'datetime'"
                        % field
                    )
                configs.append((name, field.config_parameter))
            else:
                others.append(name)

        modules = IrModule.concat(*module_recs) if module_recs else IrModule
        _debug.perf.count(
            "settings_fields_classified",
            model=self._name,
            fields=len(fnames),
            defaults=len(defaults),
            groups=len(groups),
            modules=len(modules),
            config=len(configs),
            other=len(others),
        )
        return {
            "default": defaults,
            "group": groups,
            "module": modules,
            "config": configs,
            "other": others,
        }

    @api.model
    def get_values(self) -> dict[str, Any]:
        return {}

    @api.model
    def default_get(self, fields: list[str]) -> dict[str, Any]:
        res = super().default_get(fields)
        if not fields:
            _debug.logic("settings_defaults_skipped", model=self._name)
            return res

        IrDefault = self.env["ir.default"]
        IrConfigParameter = self.env["ir.config_parameter"].sudo()
        classified = self._get_fields_classified(fields)

        for name, model, field in classified["default"]:
            value = IrDefault._get(model, field)
            if value is not None:
                res[name] = value

        for name, groups, implied_group in classified["group"]:
            res[name] = all(implied_group in group.all_implied_ids for group in groups)
            if self._fields[name].type == "selection":
                res[name] = str(int(res[name]))

        for module in classified["module"]:
            res[f"module_{module.name}"] = module.state in (
                "installed",
                "to install",
                "to upgrade",
            )

        WARNING_MESSAGE = (
            "Error when converting value %r of field %s for ir.config.parameter %r"
        )
        for name, icp in classified["config"]:
            field = self._fields[name]
            default_value = (
                field.default(self) if callable(field.default) else field.default
            )
            value = IrConfigParameter.get_param(icp, default_value or False)
            if value is not False:
                match field.type:
                    case "many2one":
                        try:
                            value = (
                                self.env[field.comodel_name]
                                .browse(int(value))
                                .exists()
                                .id
                            )
                        except ValueError, TypeError:
                            _logger.warning(WARNING_MESSAGE, value, field, icp)
                            _debug.logic(
                                "config_param_unconvertible", setting=name, key=icp
                            )
                            value = False
                    case "integer":
                        try:
                            value = int(value)
                        except ValueError, TypeError:
                            _logger.warning(WARNING_MESSAGE, value, field, icp)
                            value = 0
                    case "float":
                        try:
                            value = float(value)
                        except ValueError, TypeError:
                            _logger.warning(WARNING_MESSAGE, value, field, icp)
                            value = 0.0
                    case "boolean":
                        value = str(value) == "True"
                    case "selection":
                        if value not in dict(field._description_selection(self.env)):
                            _logger.warning(WARNING_MESSAGE, value, field, icp)
                            value = False
            res[name] = value

        res.update(self.get_values())
        _debug.pipeline(
            "settings_defaults",
            fields=len(fields),
            defaults=len(classified["default"]),
            groups=len(classified["group"]),
            modules=len(classified["module"]),
            config=len(classified["config"]),
        )

        return res

    def set_values(self) -> None:
        if not self.env.is_admin():
            _debug.logic("set_values_refused", model=self._name, uid=self.env.uid)
            raise AccessError(
                self.env._("Only administrators can change system settings.")
            )

        self = self.with_context(active_test=False)
        stash = self.env.cr.cache.get(SETTINGS_CLASSIFIED_CACHE_KEY)
        classified = (stash or {}).get(self._name) or self._get_fields_classified()
        compared_names = [name for name, _model, _field in classified["default"]]
        compared_names += [name for name, _groups, _implied in classified["group"]]
        current_settings = self.default_get(compared_names)
        _debug.pipeline(
            "settings_set_values",
            model=self._name,
            stashed=bool(stash and stash.get(self._name)),
            compared=len(compared_names),
        )

        IrDefault = self.env["ir.default"].sudo()
        for name, model, field in classified["default"]:
            if isinstance(self[name], models.BaseModel):
                if self._fields[name].type == "many2one":
                    value = self[name].id
                else:
                    value = self[name].ids
            else:
                value = self[name]
            if name not in current_settings or value != current_settings[name]:
                _debug.logic("setting_default", setting=name, model=model, field=field)
                IrDefault.set(model, field, value)

        for name, groups, implied_group in sorted(
            classified["group"], key=lambda k: bool(int(self[k[0]] or 0))
        ):
            groups = groups.sudo()
            implied_group = implied_group.sudo()
            if self[name] == current_settings[name]:
                continue
            _debug.logic(
                "setting_group",
                setting=name,
                enabled=bool(self[name] and int(self[name])),
                implied_group=implied_group.id,
            )
            if self[name] and int(self[name]):
                groups._add_implied_group(implied_group)
            else:
                groups._remove_group(implied_group)

        IrConfigParameter = self.env["ir.config_parameter"].sudo()
        changed_params = 0  # debuglog
        for name, icp in classified["config"]:
            field = self._fields[name]
            value = self[name]
            current_value = IrConfigParameter.get_param(icp)

            if field.type == "char":
                value = (value or "").strip() or False
            elif field.type in ("integer", "float"):
                value = repr(value) if value is not None else False
            elif field.type == "many2one":
                value = value.id
            elif field.type == "boolean":
                value = str(bool(value))

            if current_value == str(value) or current_value == value:
                continue
            _debug.logic("setting_config_param", setting=name, key=icp)
            IrConfigParameter.set_param(icp, value)
            changed_params += 1  # debuglog
        _debug.perf.count(
            "settings_config_params_written",
            model=self._name,
            checked=len(classified["config"]),
            changed=changed_params,
        )

    def execute(self) -> dict[str, Any]:
        self.check_singleton()
        if not self.env.is_admin():
            _debug.logic("execute_refused", model=self._name, uid=self.env.uid)
            raise AccessError(_("Only administrators can change the settings"))

        self = self.with_context(active_test=False)
        classified = self._get_fields_classified()

        stash = self.env.cr.cache.setdefault(SETTINGS_CLASSIFIED_CACHE_KEY, {})
        stash[self._name] = classified
        try:
            self.set_values()
        finally:
            stash.pop(self._name, None)

        to_install = classified["module"].filtered(
            lambda m: self[f"module_{m.name}"] and m.state != "installed"
        )
        to_uninstall = classified["module"].filtered(
            lambda m: (
                not self[f"module_{m.name}"] and m.state in ("installed", "to upgrade")
            )
        )

        _debug.pipeline(
            "settings_execute",
            model=self._name,
            install=to_install.mapped("name"),
            uninstall=to_uninstall.mapped("name"),
        )
        if to_install or to_uninstall:
            self.env.flush_all()

        if to_uninstall:
            return {
                "type": "ir.actions.act_window",
                "target": "new",
                "name": _("Uninstall modules"),
                "view_mode": "form",
                "res_model": "base.module.uninstall",
                "context": {
                    "default_module_ids": to_uninstall.ids,
                },
            }

        installation_status = self._install_modules(to_install)

        if installation_status:
            _debug.lifecycle("transaction_reset", model=self._name, by="install")
            self.env.transaction.reset()

        return self.env["res.config"]._next_todo_action()

    def cancel(self) -> dict[str, Any]:
        actions = self.env["ir.actions.act_window"].search(
            [("res_model", "=", self._name)], limit=1
        )
        _debug.logic("settings_cancel", model=self._name, action=actions.id)
        if actions:
            return actions.read()[0]
        return {}

    def _compute_display_name(self) -> None:
        action = self.env["ir.actions.act_window"].search(
            [("res_model", "=", self._name)], limit=1
        )
        self.display_name = action.name or self._name

    @api.model
    def get_option_path(self, menu_xml_id: str) -> tuple[str, int]:
        ir_ui_menu = self.env.ref(menu_xml_id)
        return (ir_ui_menu.complete_name, ir_ui_menu.action.id)

    @api.model
    def get_option_name(self, full_field_name: str) -> str:
        model_name, field_name = full_field_name.rsplit(".", 1)
        return self.env[model_name].fields_get([field_name])[field_name]["string"]

    @api.model
    def prepare_config_warning(self, msg: str) -> RedirectWarning | UserError:
        self = self.sudo()

        regex_path = r"%\(((?:menu|field):[a-z_\.]*)\)s"
        references = re.findall(regex_path, msg, flags=re.IGNORECASE)

        values = {}
        action_id = None
        for item in references:
            ref_type, ref = item.split(":")
            if ref_type == "menu":
                values[item], action_id = self.get_option_path(ref)
            elif ref_type == "field":
                values[item] = self.get_option_name(ref)

        _debug.logic(
            "config_warning", references=len(references), redirect=bool(action_id)
        )
        if action_id:
            return RedirectWarning(
                msg % values, action_id, _("Go to the configuration panel")
            )
        return UserError(msg % values)

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        dropped = 0  # debuglog
        for vals in vals_list:
            for field in self._fields.values():
                if not (field.name in vals and field.related and not field.readonly):
                    continue
                fname0, *fnames = field.related.split(".")
                if fname0 not in vals:
                    continue

                field0 = self._fields[fname0]
                old_value = field0.convert_to_record(
                    field0.convert_to_cache(vals[fname0], self), self
                )
                for fname in fnames:
                    old_value = next(iter(old_value), old_value)[fname]

                new_value = field.convert_to_record(
                    field.convert_to_cache(vals[field.name], self), self
                )

                if old_value == new_value:
                    vals.pop(field.name)
                    dropped += 1  # debuglog

        _debug.lifecycle(
            "settings_create", count=len(vals_list), unchanged_related_dropped=dropped
        )
        return super().create(vals_list)

    def action_view_template_user(self) -> dict[str, Any]:
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "base.action_res_users"
        )
        try:
            template_user_id = literal_eval(
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("base.template_portal_user_id", "False")
            )
        except ValueError, SyntaxError:
            template_user_id = False
        template_user = self.env["res.users"].browse(template_user_id)
        if not template_user.exists():
            _debug.logic("template_user_missing", user=template_user_id)
            raise UserError(_("Invalid template user. It seems it has been deleted."))
        action["res_id"] = template_user_id
        action["views"] = [[self.env.ref("base.view_users_form").id, "form"]]
        return action
