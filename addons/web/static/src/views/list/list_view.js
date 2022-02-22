/** @odoo-module */

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { isFalsy, isTruthy, XMLParser } from "@web/core/utils/xml";
import { Field } from "@web/fields/field";
import { ActionMenus } from "@web/search/action_menus/action_menus";
import { usePager } from "@web/search/pager_hook";
import { session } from "@web/session";
import { useModel } from "@web/views/helpers/model";
import { standardViewProps } from "@web/views/helpers/standard_view_props";
import { useSetupView } from "@web/views/helpers/view_hook";
import { Layout } from "@web/views/layout";
import { ViewNotFoundError } from "@web/views/view";
import { useViewButtons } from "@web/views/view_button/hook";
import { ViewButton } from "@web/views/view_button/view_button";
import { getActiveActions, getDecoration, processButton } from "../helpers/view_utils";
import { RelationalModel, stringToOrderBy } from "../relational_model";
import { ListRenderer } from "./list_renderer";

const { Component, onWillStart, useSubEnv } = owl;

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

        this.trigger("action-button-clicked", {
            clickParams,
            record: { resModel, resIds },
        });
    }
}

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
        return { activeFields, buttons, fields };
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
        const defaultOrder = stringToOrderBy(xmlDoc.getAttribute("default_order") || null);
        const activeFields = {};
        const columns = [];
        let buttonId = 0;
        const groupBy = {
            buttons: {},
            fields: {},
        };
        let headerButtons = [];
        const groupListArchParser = new GroupListArchParser();
        let buttonGroup;
        let limit;
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
                let { arch, fields: groupByFields } = fields[fieldName].views.groupby;
                groupByFields = Object.assign(
                    {
                        id: {
                            change_default: false,
                            company_dependent: false,
                            depends: [],
                            manual: false,
                            name: "id",
                            readonly: true,
                            required: false,
                            searchable: true,
                            sortable: true,
                            store: true,
                            string: "ID",
                            type: "integer",
                        },
                    },
                    groupByFields
                );
                const { activeFields, buttons, fields: parsedFields } = groupListArchParser.parse(
                    arch,
                    groupByFields
                );
                groupBy.buttons[fieldName] = buttons;
                groupBy.fields[fieldName] = { activeFields, fields: parsedFields };
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
            } else if (node.tagName === "tree") {
                const limitAttr = node.getAttribute("limit");
                limit = limitAttr && parseInt(limitAttr, 10);
            }
        });

        return {
            activeActions,
            editable,
            limit,
            headerButtons,
            fields: activeFields,
            columns,
            groupBy,
            defaultOrder,
            decorations,
        };
    }
}

// -----------------------------------------------------------------------------

export class ListView extends Component {
    setup() {
        this.actionService = useService("action");
        this.dialogService = useService("dialog");
        this.notificationService = useService("notification");
        this.user = useService("user");

        this.archInfo = new ListArchParser().parse(this.props.arch, this.props.fields);
        this.activeActions = this.archInfo.activeActions;
        this.model = useModel(RelationalModel, {
            resModel: this.props.resModel,
            fields: this.props.fields,
            activeFields: this.archInfo.fields,
            viewMode: "list",
            groupByInfo: this.archInfo.groupBy.fields,
            limit: this.archInfo.limit || this.props.limit,
            defaultOrder: this.archInfo.defaultOrder,
        });
        useViewButtons(this.model);

        onWillStart(async () => {
            this.isExportEnable = await this.user.hasGroup("base.group_allow_export");
        });

        this.archiveEnabled = "active" in this.props.fields || "x_active" in this.props.fields;

        onWillStart(async () => {
            this.isExportEnable = await this.user.hasGroup("base.group_allow_export");
        });

        useSubEnv({ model: this.model }); // do this in useModel?

        useSetupView({
            /** TODO **/
        });

        usePager(() => {
            return {
                offset: this.model.root.offset,
                limit: Math.max(this.model.root.limit, this.model.root.records.length),
                total: this.model.root.count,
                onUpdate: async ({ offset, limit }) => {
                    this.model.root.offset = offset;
                    this.model.root.limit = limit;
                    await this.model.root.load();
                    this.render();
                },
            };
        });
    }

    async openRecord(record) {
        const resIds = this.model.root.records.map((datapoint) => datapoint.resId);
        try {
            await this.actionService.switchView("form", { resId: record.resId, resIds });
        } catch (e) {
            if (e instanceof ViewNotFoundError) {
                // there's no form view in the current action
                return;
            }
            throw e;
        }
    }

    async onClickCreate() {
        if (this.archInfo.editable) {
            // add a new row
            if (this.model.root.editedRecord) {
                await this.model.root.editedRecord.save();
            }
            await this.model.root.createRecord(null, this.archInfo.editable === "top");
            this.render();
        } else {
            // switch to form view to create a new record
            try {
                await this.actionService.switchView("form", { resId: false });
            } catch (e) {
                if (e instanceof ViewNotFoundError) {
                    // there's no form view in the current action
                    return;
                }
                throw e;
            }
        }
    }

    onClickDiscard() {
        if (this.model.root.editedRecord.isNew) {
            this.model.root.removeRecord(this.model.root.editedRecord);
        } else {
            this.model.root.editedRecord.discard();
        }
    }

    async onClickSave() {
        // this is useless since we save on click outside
        // await this.editedRecord.save();
        // this.editedRecord = null;
        // this.render();
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

    onSelectDomain() {
        this.model.root.selectDomain(true);
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
        if (archive) {
            resIds = await this.model.root.archive(true);
        } else {
            resIds = await this.model.root.unarchive(true);
        }
        const total = this.model.root.count;
        if (
            isDomainSelected &&
            resIds.length === session.active_ids_limit &&
            resIds.length < total
        ) {
            this.notificationService.add(
                this.env._t(
                    `Of the ${total} records selected, only the first ${resIds.length} have been archived/unarchived.`
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
                        this.env._t(
                            `Only the first ${total} records have been deleted (out of ${resIds.length} selected)`
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
ListView.icon = "oi-table";
ListView.multiRecord = true;
ListView.components = { ActionMenus, ListViewHeaderButton, ListRenderer, Layout, ViewButton };
ListView.props = {
    ...standardViewProps,
    hasSelectors: { type: Boolean, optional: 1 },
};
ListView.defaultProps = {
    hasSelectors: true,
};

ListView.template = `web.ListView`;
ListView.buttonTemplate = "web.ListView.Buttons";
ListView.ArchParser = ListArchParser;

registry.category("views").add("list", ListView);
