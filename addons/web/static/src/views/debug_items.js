/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { editModelDebug } from "@web/core/debug/debug_utils";
import { formatDateTime, deserializeDateTime } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { formatMany2one } from "@web/views/fields/formatters";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";

import { Component, onWillStart, useState, xml } from "@odoo/owl";
import {serializeDate, serializeDateTime} from "../core/l10n/dates";

const debugRegistry = registry.category("debug");

function viewSeparator() {
    return { type: "separator", sequence: 300 };
}

debugRegistry.category("view").add("viewSeparator", viewSeparator);

//------------------------------------------------------------------------------
// Get view
//------------------------------------------------------------------------------

class GetViewDialog extends Component {
    setup() {
        this.title = _t("Get View");
    }
}
GetViewDialog.template = "web.DebugMenu.GetViewDialog";
GetViewDialog.components = { Dialog };
GetViewDialog.props = {
    arch: { type: Element },
    close: { type: Function },
};

export function getView({ component, env }) {
    return {
        type: "item",
        description: _t("Get View"),
        callback: () => {
            env.services.dialog.add(GetViewDialog, { arch: component.props.arch });
        },
        sequence: 340,
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
    let { viewId, viewType: type } = component.env.config || {}; // fallback is there for legacy
    if ("viewInfo" in component.props) {
        // legacy
        viewId = component.props.viewInfo.view_id;
        type = component.props.viewInfo.type;
        type = type === "tree" ? "list" : type;
    }
    if (!type) {
        return;
    }
    const displayName = type[0].toUpperCase() + type.slice(1);
    const description = _t("Edit View: ") + displayName;
    return {
        type: "item",
        description,
        callback: () => {
            editModelDebug(env, description, "ir.ui.view", viewId);
        },
        sequence: 350,
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
    let { searchViewId } = component.props.info || {}; // fallback is there for legacy
    if ("viewParams" in component.props) {
        //legacy
        if (!component.props.viewParams.action.controlPanelFieldsView) {
            return null;
        }
        searchViewId = component.props.viewParams.action.controlPanelFieldsView.view_id;
    }
    if (searchViewId === undefined) {
        return null;
    }
    const description = _t("Edit SearchView");
    return {
        type: "item",
        description,
        callback: () => {
            editModelDebug(env, description, "ir.ui.view", searchViewId);
        },
        sequence: 360,
    };
}

debugRegistry.category("view").add("editSearchView", editSearchView);

// -----------------------------------------------------------------------------
// View Metadata
// -----------------------------------------------------------------------------

class GetMetadataDialog extends Component {
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
GetMetadataDialog.template = "web.DebugMenu.GetMetadataDialog";
GetMetadataDialog.components = { Dialog };

export function viewMetadata({ component, env }) {
    const resId = component.model.root.resId;
    if (!resId) {
        return null; // No record
    }
    return {
        type: "item",
        description: _t("View Metadata"),
        callback: () => {
            env.services.dialog.add(GetMetadataDialog, {
                resModel: component.props.resModel,
                resId,
            });
        },
        sequence: 320,
    };
}

debugRegistry.category("form").add("viewMetadata", viewMetadata);

// -----------------------------------------------------------------------------
// View Raw Record Data
// -----------------------------------------------------------------------------

class RawRecordDialog extends Component {
    get content() {
        const record = this.props.record;
        return JSON.stringify(record, Object.keys(record).sort(), 2);
    }
}
RawRecordDialog.template = xml`
<Dialog title="props.title">
    <pre t-esc="content"/>
</Dialog>`;
RawRecordDialog.components = { Dialog };
RawRecordDialog.props = {
    record: { type: Object },
    title: { type: String },
    close: { type: Function },
};

export function viewRawRecord({ component, env }) {
    const { resId, resModel } = component.model.config;
    if (!resId) {
        return null;
    }
    const description = _t("View Raw Record Data");
    return {
        type: "item",
        description,
        callback: async () => {
            const records = await component.model.orm.read(resModel, [resId]);
            env.services.dialog.add(RawRecordDialog, {
                title: _t("Raw Record Data: %s(%s)", resModel, resId),
                record: records[0],
            });
        },
        sequence: 325,
    };
}

debugRegistry.category("form").add("viewRawRecord", viewRawRecord);

// -----------------------------------------------------------------------------
// Set Defaults
// -----------------------------------------------------------------------------

class SetDefaultDialog extends Component {
    setup() {
        this.orm = useService("orm");
        this.title = _t("Set Defaults");
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

        if(fieldToSet.constructor.name.toLowerCase() === "date"){
            fieldToSet = serializeDate(fieldToSet);
        } else if (fieldToSet.constructor.name.toLowerCase() === "datetime"){
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
SetDefaultDialog.template = "web.DebugMenu.SetDefaultDialog";
SetDefaultDialog.components = { Dialog };
SetDefaultDialog.props = {
    record: { type: Object },
    fieldNodes: { type: Object },
    close: { type: Function },
};

export function setDefaults({ component, env }) {
    return {
        type: "item",
        description: _t("Set Defaults"),
        callback: () => {
            env.services.dialog.add(SetDefaultDialog, {
                record: component.model.root,
                fieldNodes: component.props.archInfo.fieldNodes,
            });
        },
        sequence: 310,
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
    const description = _t("Manage Attachments");
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
        sequence: 330,
    };
}

debugRegistry.category("form").add("manageAttachments", manageAttachments);
