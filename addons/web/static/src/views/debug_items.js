// @ts-check
/** @odoo-module native */

import { Component, onWillStart, useState, xml } from "@odoo/owl";
import { getAction } from "@web/core/action_port";
import { editModelDebug } from "@web/core/debug/debug_utils";
import { formatMany2one } from "@web/core/formatters";
import {
    deserializeDateTime,
    formatDateTime,
    serializeDate,
    serializeDateTime,
} from "@web/core/l10n/dates";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/ui/dialog/dialog";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";

const debugRegistry = registry.category("debug");

class GetViewDialog extends Component {
    static template = "web.DebugMenu.GetViewDialog";
    static components = { Dialog };
    static props = {
        arch: { type: String },
        close: { type: Function },
    };
}

/**
 * @param {{ component: Object, env: Object }} params
 * @returns {Object}
 */
export function getView({ component, env }) {
    return {
        type: "item",
        description: _t("Computed Arch"),
        callback: () => {
            const { rawArch, viewArch } = component.env.config;
            env.services.dialog.add(GetViewDialog, {
                arch: rawArch ?? new XMLSerializer().serializeToString(viewArch),
            });
        },
        sequence: 270,
        section: "ui",
    };
}

debugRegistry.category("view").add("getView", /** @type {any} */ (getView));

class ViewProvenanceDialog extends Component {
    static template = "web.DebugMenu.ViewProvenanceDialog";
    static components = { Dialog };
    static props = {
        viewId: { type: Number },
        close: { type: Function },
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({ views: [] });
        onWillStart(async () => {
            const provenance = await this.orm.call("ir.ui.view", "get_provenance", [
                [this.props.viewId],
            ]);
            this.state.views = this.groupByView(provenance);
        });
    }

    /**
     * The nodes each view put in the combined arch, the primary first.
     * @param {Record<string, { view_id: number, xml_id: string | null, kind: string }>} provenance
     */
    groupByView(provenance) {
        const byView = new Map();
        for (const [nodeId, node] of Object.entries(provenance)) {
            if (!byView.has(node.view_id)) {
                byView.set(node.view_id, {
                    viewId: node.view_id,
                    xmlId: node.xml_id,
                    nodes: [],
                });
            }
            byView.get(node.view_id).nodes.push({ id: nodeId, kind: node.kind });
        }
        const views = [...byView.values()];
        views.sort((a, b) =>
            a.viewId === this.props.viewId
                ? -1
                : b.viewId === this.props.viewId
                  ? 1
                  : a.viewId - b.viewId,
        );
        for (const view of views) {
            view.nodes.sort((a, b) => a.id.localeCompare(b.id));
        }
        return views;
    }
}

/**
 * Which view put each node of the combined arch where it is.
 * @param {{ component: Object, env: Object }} params
 * @returns {Object | null}
 */
export function viewProvenance({ component, env }) {
    const { viewId } = component.env.config;
    if (!viewId) {
        return null;
    }
    return {
        type: "item",
        description: _t("View Provenance"),
        callback: () => {
            env.services.dialog.add(ViewProvenanceDialog, { viewId });
        },
        sequence: 275,
        section: "ui",
    };
}

debugRegistry
    .category("view")
    .add("viewProvenance", /** @type {any} */ (viewProvenance));

/**
 * @param {{ accessRights: Object, component: Object, env: Object }} params
 * @returns {Object | null}
 */
export function editView({ accessRights, component, env }) {
    if (!accessRights.canEditView) {
        return null;
    }
    const { viewId, viewType: type } = component.env.config;
    if (!type) {
        return null;
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

debugRegistry.category("view").add("editView", /** @type {any} */ (editView));

/**
 * @param {{ accessRights: Object, component: Object, env: Object }} params
 * @returns {Object | null}
 */
function editSearchView({ accessRights, component, env }) {
    if (!accessRights.canEditView) {
        return null;
    }
    const { searchViewId } = component.env.config;
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

debugRegistry
    .category("view")
    .add("editSearchView", /** @type {any} */ (editSearchView));

class GetMetadataDialog extends Component {
    /** @type {import("services").ServiceFactories["dialog"]} */
    dialogService;
    /** @type {string[]} */
    fieldNamesBlackList;
    /** @type {import("services").ServiceFactories["orm"]} */
    orm;
    /**
     * @type {{
     * id?: number,
     * xmlid?: string | false,
     * xmlids?: {xmlid: string, noupdate: boolean}[],
     * noupdate?: boolean,
     * creator?: string,
     * lastModifiedBy?: string,
     * createDate?: string,
     * writeDate?: string,
     * }}
     */
    state;

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
        const context = {
            .../** @type {any} */ (this).context,
            default_module: "__custom__",
            default_res_id: this.state.id,
            default_model: this.props.resModel,
        };
        this.dialogService.add(FormViewDialog, {
            context,
            onRecordSaved: () => this.loadMetadata(),
            resModel: "ir.model.data",
        });
    }

    async toggleNoupdate() {
        await this.orm.call("ir.model.data", "toggle_noupdate", [
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
        this.state.creator = formatMany2one(
            metadata.create_uid && { display_name: metadata.create_uid[1] },
        );
        this.state.lastModifiedBy = formatMany2one(
            metadata.write_uid && { display_name: metadata.write_uid[1] },
        );
        this.state.createDate = formatDateTime(
            deserializeDateTime(metadata.create_date),
        );
        this.state.writeDate = formatDateTime(deserializeDateTime(metadata.write_date));
    }
}

/**
 * @param {{ component: Object, env: Object }} params
 * @returns {Object | null}
 */
function viewMetadata({ component, env }) {
    const resId = component.model.root.resId;
    if (!resId) {
        return null;
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

debugRegistry.category("form").add("viewMetadata", /** @type {any} */ (viewMetadata));

function sortKeysDeep(obj) {
    if (Array.isArray(obj)) {
        return obj.map(sortKeysDeep);
    } else if (obj && typeof obj === "object") {
        return Object.keys(obj)
            .sort()
            .reduce((result, key) => {
                result[key] = sortKeysDeep(obj[key]);
                return result;
            }, {});
    }
    return obj;
}

class RawRecordDialog extends Component {
    static template = xml`
        <Dialog title="props.title">
            <pre t-esc="content"/>
        </Dialog>
    `;
    static components = { Dialog };
    static props = {
        record: { type: Object },
        title: { type: String },
        close: { type: Function },
    };
    get content() {
        const record = this.props.record;
        return JSON.stringify(sortKeysDeep(record), null, 2);
    }
}

/**
 * @param {{ component: Object, env: Object }} params
 * @returns {Object | null}
 */
function viewRawRecord({ component, env }) {
    const { resId, resModel, fields } = component.model.config;
    if (!resId) {
        return null;
    }
    const description = _t("Data");
    return {
        type: "item",
        description,
        callback: async () => {
            const serializableFields = Object.keys(fields).filter(
                (k) => fields[k].type !== "binary" && !fields[k].propertyName,
            );
            const records = await component.model.orm.read(
                resModel,
                [resId],
                serializableFields,
            );
            env.services.dialog.add(RawRecordDialog, {
                title: _t("Data: %(model)s(%(id)s)", {
                    model: resModel,
                    id: resId,
                }),
                record: records[0],
            });
        },
        sequence: 120,
        section: "record",
    };
}

debugRegistry.category("form").add("viewRawRecord", /** @type {any} */ (viewRawRecord));

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
                const valueDisplayed = this.display(
                    fieldInfo,
                    this.fieldsValues[fieldName],
                );
                const value = valueDisplayed[0];
                const displayed = valueDisplayed[1];
                const evalContext = this.props.record.evalContextWithVirtualIds;
                if (
                    !value ||
                    evaluateBooleanExpr(
                        this.activeFields[fieldName].invisible,
                        evalContext,
                    ) ||
                    evaluateBooleanExpr(
                        this.activeFields[fieldName].readonly,
                        evalContext,
                    ) ||
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
            .filter((val) => val);
    }

    getConditions() {
        return this.fieldNamesInView
            .filter((fieldName) => {
                const fieldInfo = this.fields[fieldName];
                return fieldInfo.change_default;
            })
            .map((fieldName) => {
                const fieldInfo = this.fields[fieldName];
                const valueDisplayed = this.display(
                    fieldInfo,
                    this.fieldsValues[fieldName],
                );
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
            displayed = value.display_name;
            value = value.id;
        } else if (value && fieldInfo.type === "selection") {
            const option = fieldInfo.selection.find((opt) => opt[0] === value);
            displayed = option ? option[1] : value;
        }
        if (
            (typeof displayed === "string" || displayed instanceof String) &&
            displayed.length > 60
        ) {
            displayed = `${displayed.slice(0, 57)}...`;
        }
        return [value, displayed];
    }

    async saveDefault() {
        if (!this.state.fieldToSet) {
            return;
        }
        let fieldToSet = this.defaultFields.find(
            (field) => field.name === this.state.fieldToSet,
        ).value;

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

/**
 * @param {{ component: Object, env: Object }} params
 * @returns {Object}
 */
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
debugRegistry.category("form").add("setDefaults", /** @type {any} */ (setDefaults));

/**
 * @param {{ component: Object, env: Object }} params
 * @returns {Object | null}
 */
function manageAttachments({ component, env }) {
    const resId = component.model.root.resId;
    if (!resId) {
        return null;
    }
    const description = _t("Attachments");
    return {
        type: "item",
        description,
        callback: () => {
            getAction(env).doAction({
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

debugRegistry
    .category("form")
    .add("manageAttachments", /** @type {any} */ (manageAttachments));
