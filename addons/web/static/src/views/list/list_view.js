/** @odoo-module */

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import { isFalsy, isTruthy, XMLParser } from "@web/core/utils/xml";
import { Field } from "@web/fields/field";
import { ActionMenus } from "@web/search/action_menus/action_menus";
import { usePager } from "@web/search/pager_hook";
import { session } from "@web/session";
import { useModel } from "@web/views/helpers/model";
import { standardViewProps } from "@web/views/helpers/standard_view_props";
import { useSetupView } from "@web/views/helpers/view_hook";
import { Layout } from "@web/search/layout";
import { useViewButtons } from "@web/views/view_button/hook";
import { ViewButton } from "@web/views/view_button/view_button";
import { archParseBoolean } from "@web/views/helpers/utils";
import { getActiveActions, getDecoration, processButton } from "../helpers/view_utils";
import { RelationalModel, stringToOrderBy } from "../relational_model";
import { ListRenderer } from "./list_renderer";

const { Component, onWillStart, useSubEnv, useEffect, useRef } = owl;

export class ListViewHeaderButton extends ViewButton {
    async onClick() {
        const clickParams = this.props.clickParams;
        const resIds = await this.props.getSelectedResIds();
        const resModel = this.props.resModel;
        clickParams.buttonContext = {
            active_domain: this.props.domain,
            // active_id: resIds[0], // FGE TODO
            active_ids: resIds,
            active_model: resModel,
        };

        this.env.onClickViewButton({
            clickParams,
            record: { resModel, resIds },
        });
    }
}
ListViewHeaderButton.props = [...ViewButton.props, "resModel", "domain", "getSelectedResIds"];

export class GroupListArchParser extends XMLParser {
    parse(arch, fields) {
        const activeFields = {};
        const buttons = [];
        let buttonId = 0;
        this.visitXML(arch, (node) => {
            if (node.tagName === "button") {
                buttons.push({
                    ...processButton(node),
                    id: buttonId++,
                });
            } else if (node.tagName === "field") {
                const fieldInfo = Field.parseFieldNode(node, fields, "list");
                activeFields[fieldInfo.name] = fieldInfo;
            }
        });
        return { activeFields, buttons };
    }
}

export class ListArchParser extends XMLParser {
    parse(arch, fields) {
        const xmlDoc = this.parseXML(arch);
        const activeActions = {
            ...getActiveActions(xmlDoc),
            exportXlsx: isTruthy(xmlDoc.getAttribute("export_xlsx"), true),
        };
        const decorations = getDecoration(xmlDoc);
        const editable = activeActions.edit ? xmlDoc.getAttribute("editable") : false;
        let defaultOrder = stringToOrderBy(xmlDoc.getAttribute("default_order") || null);
        const expand = xmlDoc.getAttribute("expand") === "1";
        const activeFields = {};
        const columns = [];
        let buttonId = 0;
        const groupBy = {
            buttons: {},
            fields: {},
        };
        let headerButtons = [];
        const creates = [];
        const groupListArchParser = new GroupListArchParser();
        let buttonGroup;
        let handleField = null;
        const treeAttr = {};
        let nextId = 0;
        this.visitXML(arch, (node) => {
            if (node.tagName !== "button") {
                buttonGroup = undefined;
            }
            if (node.tagName === "button") {
                const button = {
                    ...processButton(node),
                    defaultRank: "btn-link",
                    type: "button",
                    id: buttonId++,
                };
                if (buttonGroup) {
                    buttonGroup.buttons.push(button);
                } else {
                    buttonGroup = {
                        id: `column_${nextId++}`,
                        type: "button_group",
                        buttons: [button],
                        hasLabel: false,
                    };
                    columns.push(buttonGroup);
                }
            } else if (node.tagName === "field") {
                const fieldInfo = Field.parseFieldNode(node, fields, "list");
                activeFields[fieldInfo.name] = fieldInfo;
                if (fieldInfo.widget === "handle") {
                    handleField = fieldInfo.name;
                }
                if (isFalsy(node.getAttribute("invisible"), true)) {
                    const displayName = fieldInfo.FieldComponent.displayName;
                    columns.push({
                        ...fieldInfo,
                        id: `column_${nextId++}`,
                        optional: node.getAttribute("optional") || false,
                        type: "field",
                        hasLabel: !(fieldInfo.attrs.nolabel || fieldInfo.FieldComponent.noLabel),
                        label:
                            (fieldInfo.widget && displayName && displayName.toString()) ||
                            fieldInfo.string,
                    });
                }
            } else if (node.tagName === "groupby" && node.getAttribute("name")) {
                const fieldName = node.getAttribute("name");
                const xmlSerializer = new XMLSerializer();
                const groupByArch = xmlSerializer.serializeToString(node);
                const groupByFields = fields[fieldName].relatedFields;
                const groupByArchInfo = groupListArchParser.parse(groupByArch, groupByFields);
                groupBy.buttons[fieldName] = groupByArchInfo.buttons;
                groupBy.fields[fieldName] = {
                    activeFields: groupByArchInfo.activeFields,
                    fields: groupByFields,
                };
                return false;
            } else if (node.tagName === "header") {
                // AAB: not sure we need to handle invisible="1" button as the usecase seems way
                // less relevant than for fields (so for buttons, relying on the modifiers logic
                // that applies later on could be enough, even if the value is always true)
                headerButtons = [...node.children]
                    .map((node) => ({
                        ...processButton(node),
                        type: "button",
                        id: buttonId++,
                    }))
                    .filter((button) => button.modifiers.invisible !== true);
                return false;
            } else if (node.tagName === "create") {
                creates.push({
                    context: node.getAttribute("context"),
                    description: node.getAttribute("string"),
                });
            } else if (node.tagName === "tree") {
                const limitAttr = node.getAttribute("limit");
                treeAttr.limit = limitAttr && parseInt(limitAttr, 10);
                const groupsLimitAttr = node.getAttribute("groups_limit");
                treeAttr.groupsLimit = groupsLimitAttr && parseInt(groupsLimitAttr, 10);
                const noOpenAttr = node.getAttribute("no_open");
                treeAttr.noOpen = noOpenAttr && archParseBoolean(noOpenAttr);
            }
        });

        if (!defaultOrder.length && handleField) {
            defaultOrder = stringToOrderBy(handleField);
        }

        return {
            activeActions,
            creates,
            editable,
            expand,
            handleField,
            headerButtons,
            activeFields,
            columns,
            groupBy,
            defaultOrder,
            decorations,
            __rawArch: arch,
            ...treeAttr,
        };
    }
}

// -----------------------------------------------------------------------------

export class ListView extends Component {
    setup() {
        this.actionService = useService("action");
        this.dialogService = useService("dialog");
        this.notificationService = useService("notification");
        this.userService = useService("user");

        this.archInfo = new ListArchParser().parse(this.props.arch, this.props.fields);
        this.editable = this.props.editable ? this.archInfo.editable : false;
        this.activeActions = this.archInfo.activeActions;
        const fields = this.props.fields;
        this.model = useModel(RelationalModel, {
            resModel: this.props.resModel,
            fields,
            activeFields: this.archInfo.activeFields,
            viewMode: "list",
            groupByInfo: this.archInfo.groupBy.fields,
            limit: this.archInfo.limit || this.props.limit,
            defaultOrder: this.archInfo.defaultOrder,
            expand: this.archInfo.expand,
            groupsLimit: this.archInfo.groupsLimit,
        });
        useViewButtons(this.model, useRef("root"));

        onWillStart(async () => {
            this.isExportEnable = await this.userService.hasGroup("base.group_allow_export");
        });

        this.archiveEnabled =
            "active" in fields
                ? !fields.active.readonly
                : "x_active" in fields
                ? !fields.x_active.readonly
                : false;
        useSubEnv({ model: this.model }); // do this in useModel?

        useSetupView({
            /** TODO **/
            beforeLeave: async () => {
                if (this.model.root.editedRecord) {
                    if (!(await this.model.root.editedRecord.save())) {
                        throw new Error("View can't be saved");
                    }
                }
            },
        });

        usePager(() => {
            const list = this.model.root;
            return {
                offset: list.offset,
                limit: list.limit,
                total: list.count,
                onUpdate: async ({ offset, limit }) => {
                    if (this.model.root.editedRecord) {
                        if (!(await this.model.root.editedRecord.save())) {
                            return;
                        }
                    }
                    await list.load({ limit, offset });
                    this.render(true); // FIXME WOWL reactivity
                },
            };
        });

        useEffect(
            () => {
                if (this.props.onSelectionChanged) {
                    const resIds = this.model.root.selection.map((record) => record.resId);
                    this.props.onSelectionChanged(resIds);
                }
            },
            () => [this.model.root.selection.length]
        );
    }

    async openRecord(record) {
        const activeIds = this.model.root.records.map((datapoint) => datapoint.resId);
        this.props.selectRecord(record.resId, { activeIds });
    }

    async onClickCreate() {
        if (this.editable) {
            // add a new row
            if (this.model.root.editedRecord) {
                await this.model.root.editedRecord.save();
            }
            await this.model.root.createRecord({}, this.editable === "top");
            this.render();
        } else {
            await this.props.createRecord();
        }
    }

    onClickDiscard() {
        const editedRecord = this.model.root.editedRecord;
        if (editedRecord.isVirtual) {
            this.model.root.removeRecord(editedRecord);
        } else {
            editedRecord.discard();
        }
    }

    onClickSave() {
        this.model.root.editedRecord.save();
    }

    getSelectedResIds() {
        return this.model.root.getResIds(true);
    }

    getActionMenuItems() {
        const isM2MGrouped = this.model.root.isM2MGrouped;
        const otherActionItems = [];
        if (this.isExportEnable) {
            otherActionItems.push({
                description: this.env._t("Export"),
                callback: () => this.onExportData(),
            });
        }
        if (this.archiveEnabled && !isM2MGrouped) {
            otherActionItems.push({
                description: this.env._t("Archive"),
                callback: () => {
                    const dialogProps = {
                        body: this.env._t(
                            "Are you sure that you want to archive all the selected records?"
                        ),
                        confirm: () => {
                            this.toggleArchiveState(true);
                        },
                        cancel: () => {},
                    };
                    this.dialogService.add(ConfirmationDialog, dialogProps);
                },
            });
            otherActionItems.push({
                description: this.env._t("Unarchive"),
                callback: () => this.toggleArchiveState(false),
            });
        }
        if (this.activeActions.delete && !isM2MGrouped) {
            otherActionItems.push({
                description: this.env._t("Delete"),
                callback: () => this.onDeleteSelectedRecords(),
            });
        }
        return Object.assign({}, this.props.info.actionMenus, { other: otherActionItems });
    }

    async onSelectDomain() {
        this.model.root.selectDomain(true);
        if (this.props.onSelectionChanged) {
            const resIds = await this.model.root.getResIds(true);
            this.props.onSelectionChanged(resIds);
        }
    }

    get nbSelected() {
        return this.model.root.selection.length;
    }

    get isPageSelected() {
        const root = this.model.root;
        return root.selection.length === root.records.length;
    }

    get isDomainSelected() {
        return this.model.root.isDomainSelected;
    }

    get nbTotal() {
        return this.model.root.count;
    }

    /**
     * Opens the Export Dialog
     *
     * @private
     */
    onExportData() {
        console.log("onExportData");
        // this._getExportDialogWidget().open();
    }
    /**
     * Export Records in a xls file
     *
     * @private
     */
    onDirectExportData() {
        console.log("onDirectExportData");
    }
    /**
     * Called when clicking on 'Archive' or 'Unarchive' in the sidebar.
     *
     * @private
     * @param {boolean} archive
     * @returns {Promise}
     */
    async toggleArchiveState(archive) {
        let resIds;
        const isDomainSelected = this.model.root.isDomainSelected;
        const total = this.model.root.count;
        if (archive) {
            resIds = await this.model.root.archive(true);
        } else {
            resIds = await this.model.root.unarchive(true);
        }
        if (
            isDomainSelected &&
            resIds.length === session.active_ids_limit &&
            resIds.length < total
        ) {
            this.notificationService.add(
                sprintf(
                    this.env._t(
                        "Of the %d records selected, only the first %d have been archived/unarchived."
                    ),
                    resIds.length,
                    total
                ),
                { title: this.env._t("Warning") }
            );
        }
    }

    async onDeleteSelectedRecords() {
        const root = this.model.root;
        const body =
            root.isDomainSelected || root.selection.length > 1
                ? this.env._t("Are you sure you want to delete these records?")
                : this.env._t("Are you sure you want to delete this record?");
        const dialogProps = {
            body,
            confirm: async () => {
                const total = root.count;
                const resIds = await this.model.root.deleteRecords();
                if (
                    root.isDomainSelected &&
                    resIds.length === session.active_ids_limit &&
                    resIds.length < total
                ) {
                    this.notificationService.add(
                        sprintf(
                            this.env._t(
                                `Only the first %s records have been deleted (out of %s selected)`
                            ),
                            resIds.length,
                            total
                        ),
                        { title: this.env._t("Warning") }
                    );
                }
            },
            cancel: () => {},
        };
        this.dialogService.add(ConfirmationDialog, dialogProps);
    }
}

ListView.type = "list";
ListView.display_name = "List";
ListView.icon = "oi oi-view-list";
ListView.multiRecord = true;
ListView.components = { ActionMenus, ListViewHeaderButton, ListRenderer, Layout, ViewButton };
ListView.props = {
    ...standardViewProps,
    hasSelectors: { type: Boolean, optional: 1 },
    editable: { type: Boolean, optional: 1 },
    showButtons: { type: Boolean, optional: 1 },
    onSelectionChanged: { type: Function, optional: 1 },
};
ListView.defaultProps = {
    createRecord: () => {},
    hasSelectors: true,
    editable: true,
    selectRecord: () => {},
    showButtons: true,
};

ListView.template = `web.ListView`;
ListView.buttonTemplate = "web.ListView.Buttons";
ListView.ArchParser = ListArchParser;

registry.category("views").add("list", ListView);
