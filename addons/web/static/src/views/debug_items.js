/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { editModelDebug } from "@web/core/debug/debug_utils";
import { formatDateTime, deserializeDateTime } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { formatMany2one } from "@web/views/fields/formatters";
import { evalDomain } from "@web/views/utils";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";

import { Component, onWillStart, useState, xml } from "@odoo/owl";

const debugRegistry = registry.category("debug");

function viewSeparator() {
    return { type: "separator", sequence: 300 };
}

debugRegistry.category("view").add("viewSeparator", viewSeparator);

//------------------------------------------------------------------------------
// Get view
//------------------------------------------------------------------------------

class GetViewDialog extends Component {}
GetViewDialog.template = xml`
<Dialog title="this.constructor.title">
    <pre t-esc="props.arch"/>
</Dialog>`;
GetViewDialog.components = { Dialog };
GetViewDialog.props = {
    arch: { type: String },
    close: { type: Function },
};
GetViewDialog.title = _lt("Get View");

export function getView({ component, env }) {
    let { arch } = component.props;
    if ("viewInfo" in component.props) {
        //legacy
        arch = component.props.viewInfo.arch;
    }
    return {
        type: "item",
        description: env._t("Get View"),
        callback: () => {
            env.services.dialog.add(GetViewDialog, { arch });
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
    const displayName = type[0].toUpperCase() + type.slice(1);
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
    const description = env._t("Edit SearchView");
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
        this.title = this.env._t("View Metadata");
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
        description: env._t("View Metadata"),
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
// Set Defaults
// -----------------------------------------------------------------------------

class SetDefaultDialog extends Component {
    setup() {
        this.orm = useService("orm");
        this.title = this.env._t("Set Defaults");
        this.state = {
            fieldToSet: "",
            condition: "",
            scope: "self",
        };
        const root = this.props.component.model.root;
        this.fields = root.fields;
        this.fieldsInfo = root.activeFields;
        this.fieldNamesInView = root.fieldNames;
        this.fieldNamesBlackList = ["message_attachment_count"];
        this.fieldsValues = root.data;
        this.modifierDatas = {};
        this.fieldNamesInView.forEach((fieldName) => {
            this.modifierDatas[fieldName] = this.fieldsInfo[fieldName].modifiers;
        });
        this.defaultFields = this.getDefaultFields();
        this.conditions = this.getConditions();
    }

    getDefaultFields() {
        return this.fieldNamesInView
            .filter((fieldName) => !this.fieldNamesBlackList.includes(fieldName))
            .map((fieldName) => {
                const modifierData = this.modifierDatas[fieldName];
                let invisibleOrReadOnly;
                if (modifierData) {
                    const evalContext = this.props.component.model.root.evalContext;
                    invisibleOrReadOnly =
                        evalDomain(modifierData.invisible, evalContext) ||
                        evalDomain(modifierData.readonly, evalContext);
                }
                const fieldInfo = this.fields[fieldName];
                const valueDisplayed = this.display(fieldInfo, this.fieldsValues[fieldName]);
                const value = valueDisplayed[0];
                const displayed = valueDisplayed[1];
                // ignore fields which are empty, invisible, readonly, o2m or m2m
                if (
                    !value ||
                    invisibleOrReadOnly ||
                    fieldInfo.type === "one2many" ||
                    fieldInfo.type === "many2many" ||
                    fieldInfo.type === "binary" ||
                    this.fieldsInfo[fieldName].options.isPassword
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
        const fieldToSet = this.defaultFields.find((field) => {
            return field.name === this.state.fieldToSet;
        }).value;
        await this.orm.call("ir.default", "set", [
            this.props.resModel,
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

export function setDefaults({ component, env }) {
    return {
        type: "item",
        description: env._t("Set Defaults"),
        callback: () => {
            env.services.dialog.add(SetDefaultDialog, {
                resModel: component.props.resModel,
                component,
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
    const description = env._t("Manage Attachments");
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
                },
            });
        },
        sequence: 330,
    };
}

debugRegistry.category("form").add("manageAttachments", manageAttachments);
