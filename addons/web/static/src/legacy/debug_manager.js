/** @odoo-module **/

import { editModelDebug } from "../core/debug/debug_service";
import { Dialog } from "../core/dialog/dialog";
import { formatDateTime, parseDateTime } from "../core/l10n/dates";
import { _lt } from "../core/l10n/translation";
import { registry } from "../core/registry";
import { formatMany2one } from "../fields/format";
import { json_node_to_xml } from "../views/view_utils";

const { hooks, tags } = owl;
const { useState } = hooks;

// Action items

function actionSeparator() {
    return {
        type: "separator",
        sequence: 100,
    };
}

function accessSeparator({ accessRights, action }) {
    const { canSeeModelAccess, canSeeRecordRules } = accessRights;
    if (!action.res_model || (!canSeeModelAccess && !canSeeRecordRules)) {
        return null;
    }
    return {
        type: "separator",
        sequence: 200,
    };
}

function editAction({ action, env }) {
    if (!action.id) {
        return null;
    }
    const description = env._t("Edit Action");
    return {
        type: "item",
        description,
        callback: () => {
            editModelDebug(env, description, action.type, action.id);
        },
        sequence: 110,
    };
}

function viewFields({ action, env }) {
    if (!action.res_model) {
        return null;
    }
    const description = env._t("View Fields");
    return {
        type: "item",
        description,
        callback: async () => {
            const modelId = (
                await env.services.orm.search("ir.model", [["model", "=", action.res_model]], {
                    limit: 1,
                })
            )[0];
            env.services.action.doAction({
                res_model: "ir.model.fields",
                name: description,
                views: [
                    [false, "list"],
                    [false, "form"],
                ],
                domain: [["model_id", "=", modelId]],
                type: "ir.actions.act_window",
                context: {
                    default_model_id: modelId,
                },
            });
        },
        sequence: 120,
    };
}

function manageFilters({ action, env }) {
    if (!action.res_model) {
        return null;
    }
    const description = env._t("Manage Filters");
    return {
        type: "item",
        description,
        callback: () => {
            // manage_filters
            env.services.action.doAction({
                res_model: "ir.filters",
                name: description,
                views: [
                    [false, "list"],
                    [false, "form"],
                ],
                type: "ir.actions.act_window",
                context: {
                    search_default_my_filters: true,
                    search_default_model_id: action.res_model,
                },
            });
        },
        sequence: 130,
    };
}

function technicalTranslation({ action, env }) {
    if (!action.res_model) {
        return null;
    }
    return {
        type: "item",
        description: env._t("Technical Translation"),
        callback: async () => {
            const result = await env.services.orm.call(
                "ir.translation",
                "get_technical_translations",
                [action.res_model]
            );
            env.services.action.doAction(result);
        },
        sequence: 140,
    };
}

function viewAccessRights({ accessRights, action, env }) {
    if (!action.res_model || !accessRights.canSeeModelAccess) {
        return null;
    }
    const description = env._t("View Access Rights");
    return {
        type: "item",
        description,
        callback: async () => {
            const modelId = (
                await env.services.orm.search("ir.model", [["model", "=", action.res_model]], {
                    limit: 1,
                })
            )[0];
            env.services.action.doAction({
                res_model: "ir.model.access",
                name: description,
                views: [
                    [false, "list"],
                    [false, "form"],
                ],
                domain: [["model_id", "=", modelId]],
                type: "ir.actions.act_window",
                context: {
                    default_model_id: modelId,
                },
            });
        },
        sequence: 210,
    };
}

function viewRecordRules({ accessRights, action, env }) {
    if (!action.res_model || !accessRights.canSeeRecordRules) {
        return null;
    }
    const description = env._t("Model Record Rules");
    return {
        type: "item",
        description: env._t("View Record Rules"),
        callback: async () => {
            const modelId = (
                await env.services.orm.search("ir.model", [["model", "=", action.res_model]], {
                    limit: 1,
                })
            )[0];
            env.services.action.doAction({
                res_model: "ir.rule",
                name: description,
                views: [
                    [false, "list"],
                    [false, "form"],
                ],
                domain: [["model_id", "=", modelId]],
                type: "ir.actions.act_window",
                context: {
                    default_model_id: modelId,
                },
            });
        },
        sequence: 220,
    };
}

class FieldViewGetDialog extends Dialog {}
FieldViewGetDialog.props = Object.assign({}, Dialog.props, { arch: { type: String } });
FieldViewGetDialog.bodyTemplate = tags.xml`<pre t-esc="props.arch"/>`;
FieldViewGetDialog.title = _lt("Fields View Get");

class GetMetadataDialog extends Dialog {
    setup() {
        super.setup();
        this.state = useState({});
    }

    async willStart() {
        await this.getMetadata();
    }

    async toggleNoupdate() {
        await this.env.services.orm.call("ir.model.data", "toggle_noupdate", [
            this.props.res_model,
            this.state.id,
        ]);
        await this.getMetadata();
    }

    async getMetadata() {
        const metadata = (
            await this.env.services.orm.call(this.props.res_model, "get_metadata", [
                this.props.selectedIds,
            ])
        )[0];
        this.state.id = metadata.id;
        this.state.xmlid = metadata.xmlid;
        this.state.creator = formatMany2one(metadata.create_uid);
        this.state.lastModifiedBy = formatMany2one(metadata.write_uid);
        this.state.noupdate = metadata.noupdate;
        this.state.create_date = formatDateTime(parseDateTime(metadata.create_date));
        this.state.write_date = formatDateTime(parseDateTime(metadata.write_date));
    }
}
GetMetadataDialog.bodyTemplate = "web.DebugMenu.getMetadataBody";
GetMetadataDialog.title = _lt("View Metadata");

class SetDefaultDialog extends Dialog {
    setup() {
        super.setup();
        this.state = {
            fieldToSet: "",
            condition: "",
            scope: "self",
        };
        this.dataWidgetState = this.getDataWidgetState();
        this.defaultFields = this.getDefaultFields();
        this.conditions = this.getConditions();
    }

    getDataWidgetState() {
        const renderer = this.props.component.widget.renderer;
        const state = renderer.state;
        const fields = state.fields;
        const fieldsInfo = state.fieldsInfo.form;
        const fieldNamesInView = state.getFieldNames();
        const fieldNamesOnlyOnView = ["message_attachment_count"];
        const fieldsValues = state.data;
        const modifierDatas = {};
        fieldNamesInView.forEach((fieldName) => {
            modifierDatas[fieldName] = renderer.allModifiersData.find((modifierdata) => {
                return modifierdata.node.attrs.name === fieldName;
            });
        });
        return {
            fields,
            fieldsInfo,
            fieldNamesInView,
            fieldNamesOnlyOnView,
            fieldsValues,
            modifierDatas,
            stateId: state.id,
        };
    }

    getDefaultFields() {
        const {
            fields,
            fieldsInfo,
            fieldNamesInView,
            fieldNamesOnlyOnView,
            fieldsValues,
            modifierDatas,
            stateId,
        } = this.dataWidgetState;
        return fieldNamesInView
            .filter((fieldName) => !fieldNamesOnlyOnView.includes(fieldName))
            .map((fieldName) => {
                const modifierData = modifierDatas[fieldName];
                let invisibleOrReadOnly;
                if (modifierData) {
                    const evaluatedModifiers = modifierData.evaluatedModifiers[stateId];
                    invisibleOrReadOnly =
                        evaluatedModifiers.invisible || evaluatedModifiers.readonly;
                }
                const fieldInfo = fields[fieldName];
                const valueDisplayed = this.display(fieldInfo, fieldsValues[fieldName]);
                const value = valueDisplayed[0];
                const displayed = valueDisplayed[1];
                // ignore fields which are empty, invisible, readonly, o2m
                // or m2m
                if (
                    !value ||
                    invisibleOrReadOnly ||
                    fieldInfo.type === "one2many" ||
                    fieldInfo.type === "many2many" ||
                    fieldInfo.type === "binary" ||
                    fieldsInfo[fieldName].options.isPassword ||
                    fieldInfo.depends.length !== 0
                ) {
                    return false;
                }
                return {
                    name: fieldName,
                    string: fieldInfo.string,
                    value: value,
                    displayed: displayed,
                };
            })
            .filter((val) => val)
            .sort((field) => field.string);
    }

    getConditions() {
        const { fields, fieldNamesInView, fieldsValues } = this.dataWidgetState;
        return fieldNamesInView
            .filter((fieldName) => {
                const fieldInfo = fields[fieldName];
                return fieldInfo.change_default;
            })
            .map((fieldName) => {
                const fieldInfo = fields[fieldName];
                const valueDisplayed = this.display(fieldInfo, fieldsValues[fieldName]);
                const value = valueDisplayed[0];
                const displayed = valueDisplayed[1];
                return {
                    name: fieldName,
                    string: fieldInfo.string,
                    value: value,
                    displayed: displayed,
                };
            });
    }

    display(fieldInfo, value) {
        let displayed = value;
        if (value && fieldInfo.type === "many2one") {
            displayed = value.data.display_name;
            value = value.data.id;
        } else if (value && fieldInfo.type === "selection") {
            displayed = fieldInfo.selection.find((option) => {
                return option[0] === value;
            })[1];
        }
        return [value, displayed];
    }

    async saveDefault() {
        if (!this.state.fieldToSet) {
            // TODO $defaults.parent().addClass('o_form_invalid');
            // It doesn't work in web.
            // Good solution: Create a FormView
            return;
        }
        const fieldToSet = this.defaultFields.find((field) => {
            return field.name === this.state.fieldToSet;
        }).value;
        await this.env.services.orm.call("ir.default", "set", [
            this.props.res_model,
            this.state.fieldToSet,
            fieldToSet,
            this.state.scope === "self",
            true,
            this.state.condition || false,
        ]);
        this.trigger("dialog-closed");
    }
}
SetDefaultDialog.bodyTemplate = "web.DebugMenu.setDefaultBody";
SetDefaultDialog.footerTemplate = "web.DebugMenu.SetDefaultFooter";
SetDefaultDialog.title = _lt("Set Default");

function viewSeparator() {
    return {
        type: "separator",
        sequence: 300,
    };
}

function fieldsViewGet({ component, env }) {
    return {
        type: "item",
        description: env._t("Fields View Get"),
        callback: () => {
            const props = {
                arch: json_node_to_xml(component.props.viewInfo.arch, true, 0),
            };
            env.services.dialog.open(FieldViewGetDialog, props);
        },
        sequence: 340,
    };
}

export function editView({ accessRights, action, component, env }) {
    if (!accessRights.canEditView) {
        return null;
    }
    const { viewId, viewType } = component.widget;
    const displayName = action.views
        .find((v) => v.type === viewType)
        .name.toString();
    const description = env._t("Edit View: ") + displayName;
    return {
        type: "item",
        description,
        callback: () => {
            editModelDebug(env, description, "ir.ui.view", viewId);
        },
        sequence: 350,
    };
}

function editControlPanelView({ accessRights, component, env }) {
    if (!accessRights.canEditView) {
        return null;
    }
    const description = env._t("Edit ControlPanelView");
    return {
        type: "item",
        description,
        callback: () => {
            editModelDebug(
                env,
                description,
                "ir.ui.view",
                component.props.viewInfo.view_id
            );
        },
        sequence: 360,
    };
}

// Form view itemss

function setDefaults({ action, component, env }) {
    return {
        type: "item",
        description: env._t("Set Defaults"),
        callback: () => {
            env.services.dialog.open(SetDefaultDialog, {
                res_model: action.res_model,
                component,
            });
        },
        sequence: 310,
    };
}

function viewMetadata({ action, component, env }) {
    const selectedIds = component.widget.getSelectedIds();
    if (selectedIds.length !== 1) {
        return null;
    }
    return {
        type: "item",
        description: env._t("View Metadata"),
        callback: () => {
            env.services.dialog.open(GetMetadataDialog, {
                res_model: action.res_model,
                selectedIds,
            });
        },
        sequence: 320,
    };
}

function manageAttachments({ action, component, env }) {
    const selectedIds = component.widget.getSelectedIds();
    const description = env._t("Manage Attachments");
    if (selectedIds.length !== 1) {
        return null;
    }
    return {
        type: "item",
        description,
        callback: () => {
            const selectedId = selectedIds[0];
            env.services.action.doAction({
                res_model: "ir.attachment",
                name: description,
                views: [
                    [false, "list"],
                    [false, "form"],
                ],
                type: "ir.actions.act_window",
                domain: [
                    ["res_model", "=", action.res_model],
                    ["res_id", "=", selectedId],
                ],
                context: {
                    default_res_model: action.res_model,
                    default_res_id: selectedId,
                },
            });
        },
        sequence: 330,
    };
}

const debugRegistry = registry.category("debug");

debugRegistry
    .category("action")
        .add("actionSeparator", actionSeparator)
        .add("editAction", editAction)
        .add("viewFields", viewFields)
        .add("manageFilters", manageFilters)
        .add("technicalTranslation", technicalTranslation)
        .add("accessSeparator", accessSeparator)
        .add("viewAccessRights", viewAccessRights)
        .add("viewRecordRules", viewRecordRules)

debugRegistry
    .category("view")
        .add("viewSeparator", viewSeparator)
        .add("fieldsViewGet", fieldsViewGet)
        .add("editView", editView)
        .add("editControlPanelView", editControlPanelView)

debugRegistry
    .category("form")
        .add("setDefaults", setDefaults)
        .add("viewMetadata", viewMetadata)
        .add("manageAttachments", manageAttachments);
