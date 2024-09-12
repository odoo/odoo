import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { editModelDebug } from "@web/core/debug/debug_utils";
import { formatDateTime, deserializeDateTime } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { formatMany2one } from "@web/views/fields/formatters";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";

import { Component, onWillStart, useState } from "@odoo/owl";
import { serializeDate, serializeDateTime } from "../core/l10n/dates";
import { redirect } from "@web/core/utils/urls";
import { browser } from "@web/core/browser/browser";

const debugRegistry = registry.category("debug");

//------------------------------------------------------------------------------
// Get view
//------------------------------------------------------------------------------

class GetViewDialog extends Component {
    static template = "web.DebugMenu.GetViewDialog";
    static components = { Dialog };
    static props = {
        arch: { type: String },
        close: { type: Function },
    };
}

export function getView({ component, env }) {
    return {
        type: "item",
        description: _t("Computed Arch"),
        callback: () => {
            env.services.dialog.add(GetViewDialog, { arch: component.env.config.rawArch });
        },
        sequence: 270,
        section: "ui",
    };
}

debugRegistry.category("view").add("getView", getView);

//------------------------------------------------------------------------------
// Edit View
//------------------------------------------------------------------------------

export function editView({ accessRights, component, env }) {
    if (!accessRights.canEditView) {
        return null;
    }
    const { viewId, viewType: type } = component.env.config;
    if (!type) {
        return;
    }
    const displayName = type[0].toUpperCase() + type.slice(1);
    const description = _t("View: %(displayName)s", { displayName });
    return {
        type: "item",
        description,
        callback: () => {
            editModelDebug(env, description, "ir.ui.view", viewId);
        },
        sequence: 240,
        section: "ui",
    };
}

debugRegistry.category("view").add("editView", editView);

//------------------------------------------------------------------------------
// Edit SearchView
//------------------------------------------------------------------------------

export function editSearchView({ accessRights, component, env }) {
    if (!accessRights.canEditView) {
        return null;
    }
    const { searchViewId } = component.componentProps.info;
    if (searchViewId === undefined) {
        return null;
    }
    const description = _t("SearchView");
    return {
        type: "item",
        description,
        callback: () => {
            editModelDebug(env, description, "ir.ui.view", searchViewId);
        },
        sequence: 230,
        section: "ui",
    };
}

debugRegistry.category("view").add("editSearchView", editSearchView);

// -----------------------------------------------------------------------------
// View Metadata
// -----------------------------------------------------------------------------

class GetMetadataDialog extends Component {
    static template = "web.DebugMenu.GetMetadataDialog";
    static components = { Dialog };
    static props = {
        resModel: String,
        resId: Number,
        close: Function,
    };
    setup() {
        this.orm = useService("orm");
        this.dialogService = useService("dialog");
        this.title = _t("View Metadata");
        this.state = useState({});
        onWillStart(() => this.loadMetadata());
    }

    onClickCreateXmlid() {
        const context = Object.assign({}, this.context, {
            default_module: "__custom__",
            default_res_id: this.state.id,
            default_model: this.props.resModel,
        });
        this.dialogService.add(FormViewDialog, {
            context,
            onRecordSaved: () => this.loadMetadata(),
            resModel: "ir.model.data",
        });
    }

    async toggleNoupdate() {
        await this.env.services.orm.call("ir.model.data", "toggle_noupdate", [
            this.props.resModel,
            this.state.id,
        ]);
        await this.loadMetadata();
    }

    async loadMetadata() {
        const args = [[this.props.resId]];
        const result = await this.orm.call(this.props.resModel, "get_metadata", args);
        const metadata = result[0];
        this.state.id = metadata.id;
        this.state.xmlid = metadata.xmlid;
        this.state.xmlids = metadata.xmlids;
        this.state.noupdate = metadata.noupdate;
        this.state.creator = formatMany2one(metadata.create_uid);
        this.state.lastModifiedBy = formatMany2one(metadata.write_uid);
        this.state.createDate = formatDateTime(deserializeDateTime(metadata.create_date));
        this.state.writeDate = formatDateTime(deserializeDateTime(metadata.write_date));
    }
}

export function viewMetadata({ component, env }) {
    const resId = component.model.root.resId;
    if (!resId) {
        return null; // No record
    }
    return {
        type: "item",
        description: _t("Metadata"),
        callback: () => {
            env.services.dialog.add(GetMetadataDialog, {
                resModel: component.props.resModel,
                resId,
            });
        },
        sequence: 110,
        section: "record",
    };
}

debugRegistry.category("form").add("viewMetadata", viewMetadata);

// -----------------------------------------------------------------------------
// View Raw Record Data
// -----------------------------------------------------------------------------

export function viewRawRecord({ component }) {
    const description = _t("Data");
    return {
        type: "item",
        description,
        callback: async () => {
            const url = new URL(browser.location);
            url.pathname = url.pathname.replace(/^\/odoo/, "json");
            redirect(url);
        },
        sequence: 120,
        get section() {
            return component.env.config.viewType === "form" ? "record" : "records";
        },
    };
}

debugRegistry.category("view").add("viewRawRecord", viewRawRecord);

// -----------------------------------------------------------------------------
// Set Defaults
// -----------------------------------------------------------------------------

class SetDefaultDialog extends Component {
    static template = "web.DebugMenu.SetDefaultDialog";
    static components = { Dialog };
    static props = {
        record: { type: Object },
        fieldNodes: { type: Object },
        close: { type: Function },
    };

    setup() {
        this.orm = useService("orm");
        this.state = {
            fieldToSet: "",
            condition: "",
            scope: "self",
        };
        this.fields = this.props.record.fields;
        this.activeFields = this.props.record.activeFields;
        this.fieldNamesInView = this.props.record.fieldNames;
        this.fieldNamesBlackList = ["message_attachment_count"];
        this.fieldsValues = this.props.record.data;
        this.modifierDatas = {};
        this.defaultFields = this.getDefaultFields();
        this.conditions = this.getConditions();
    }

    getDefaultFields() {
        return this.fieldNamesInView
            .filter((fieldName) => !this.fieldNamesBlackList.includes(fieldName))
            .map((fieldName) => {
                const fieldInfo = this.fields[fieldName];
                const valueDisplayed = this.display(fieldInfo, this.fieldsValues[fieldName]);
                const value = valueDisplayed[0];
                const displayed = valueDisplayed[1];
                const evalContext = this.props.record.evalContextWithVirtualIds;
                // ignore fields which are empty, invisible, readonly, o2m or m2m
                if (
                    !value ||
                    evaluateBooleanExpr(this.activeFields[fieldName].invisible, evalContext) ||
                    evaluateBooleanExpr(this.activeFields[fieldName].readonly, evalContext) ||
                    fieldInfo.type === "one2many" ||
                    fieldInfo.type === "many2many" ||
                    fieldInfo.type === "binary" ||
                    Object.entries(this.props.fieldNodes)
                        .filter(([key, value]) => value.name === fieldName)
                        .some(([key, value]) => value.options.isPassword)
                ) {
                    return false;
                }
                return {
                    name: fieldName,
                    string: fieldInfo.string,
                    value,
                    displayed,
                };
            })
            .filter((val) => val)
            .sort((field) => field.string);
    }

    getConditions() {
        return this.fieldNamesInView
            .filter((fieldName) => {
                const fieldInfo = this.fields[fieldName];
                return fieldInfo.change_default;
            })
            .map((fieldName) => {
                const fieldInfo = this.fields[fieldName];
                const valueDisplayed = this.display(fieldInfo, this.fieldsValues[fieldName]);
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
            displayed = value[1];
            value = value[0];
        } else if (value && fieldInfo.type === "selection") {
            displayed = fieldInfo.selection.find((option) => {
                return option[0] === value;
            })[1];
        }
        return [value, displayed];
    }

    async saveDefault() {
        if (!this.state.fieldToSet) {
            return;
        }
        let fieldToSet = this.defaultFields.find((field) => {
            return field.name === this.state.fieldToSet;
        }).value;

        if (fieldToSet.constructor.name.toLowerCase() === "date") {
            fieldToSet = serializeDate(fieldToSet);
        } else if (fieldToSet.constructor.name.toLowerCase() === "datetime") {
            fieldToSet = serializeDateTime(fieldToSet);
        }
        await this.orm.call("ir.default", "set", [
            this.props.record.resModel,
            this.state.fieldToSet,
            fieldToSet,
            this.state.scope === "self",
            true,
            this.state.condition || false,
        ]);
        this.props.close();
    }
}

export function setDefaults({ component, env }) {
    return {
        type: "item",
        description: _t("Set Default Values"),
        callback: () => {
            env.services.dialog.add(SetDefaultDialog, {
                record: component.model.root,
                fieldNodes: component.props.archInfo.fieldNodes,
            });
        },
        sequence: 150,
        section: "record",
    };
}
debugRegistry.category("form").add("setDefaults", setDefaults);

//------------------------------------------------------------------------------
// Manage Attachments
//------------------------------------------------------------------------------

export function manageAttachments({ component, env }) {
    const resId = component.model.root.resId;
    if (!resId) {
        return null; // No record
    }
    const description = _t("Attachments");
    return {
        type: "item",
        description,
        callback: () => {
            env.services.action.doAction({
                res_model: "ir.attachment",
                name: description,
                views: [
                    [false, "list"],
                    [false, "form"],
                ],
                type: "ir.actions.act_window",
                domain: [
                    ["res_model", "=", component.props.resModel],
                    ["res_id", "=", resId],
                ],
                context: {
                    default_res_model: component.props.resModel,
                    default_res_id: resId,
                    skip_res_field_check: true,
                },
            });
        },
        sequence: 140,
        section: "record",
    };
}

debugRegistry.category("form").add("manageAttachments", manageAttachments);
