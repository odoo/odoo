/** @odoo-module */

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { download } from "@web/core/network/download";
import { evaluateExpr } from "@web/core/py_js/py";
import { unique } from "@web/core/utils/arrays";
import { useService, useBus } from "@web/core/utils/hooks";
import { omit } from "@web/core/utils/objects";
import { sprintf } from "@web/core/utils/strings";
import { ActionMenus, STATIC_ACTIONS_GROUP_NUMBER } from "@web/search/action_menus/action_menus";
import { Layout } from "@web/search/layout";
import { usePager } from "@web/search/pager_hook";
import { session } from "@web/session";
import { useModel } from "@web/views/model";
import { DynamicRecordList } from "@web/views/relational_model";
import { standardViewProps } from "@web/views/standard_view_props";
import { MultiRecordViewButton } from "@web/views/view_button/multi_record_view_button";
import { ViewButton } from "@web/views/view_button/view_button";
import { useViewButtons } from "@web/views/view_button/view_button_hook";
import { ExportDataDialog } from "@web/views/view_dialogs/export_data_dialog";
import { useSetupView } from "@web/views/view_hook";
import { ListConfirmationDialog } from "./list_confirmation_dialog";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { useSearchBarToggler } from "@web/search/search_bar/search_bar_toggler";
import { CogMenu } from "@web/search/cog_menu/cog_menu";

import {
    Component,
    onMounted,
    onWillPatch,
    onWillStart,
    useEffect,
    useRef,
    useSubEnv,
} from "@odoo/owl";

// -----------------------------------------------------------------------------

export class ListController extends Component {
    setup() {
        this.actionService = useService("action");
        this.dialogService = useService("dialog");
        this.notificationService = useService("notification");
        this.userService = useService("user");
        this.rpc = useService("rpc");
        this.rootRef = useRef("root");

        this.archInfo = this.props.archInfo;
        this.activeActions = this.archInfo.activeActions;
        this.editable =
            this.activeActions.edit && this.props.editable ? this.archInfo.editable : false;
        this.model = useModel(this.props.Model, this.modelParams);

        // In multi edition, we save or notify invalidity directly when a field is updated, which
        // occurs on the change event for input fields. But we don't want to do it when clicking on
        // "Discard". So we set a flag on mousedown (which triggers the update) to block the multi
        // save or invalid notification.
        // However, if the mouseup (and click) is done outside "Discard", we finally want to do it.
        // We use `nextActionAfterMouseup` for this purpose: it registers a callback to execute if
        // the mouseup following a mousedown on "Discard" isn't done on "Discard".
        this.hasMousedownDiscard = false;
        this.nextActionAfterMouseup = null;

        onWillStart(async () => {
            this.isExportEnable = await this.userService.hasGroup("base.group_allow_export");
        });

        onMounted(() => {
            const { rendererScrollPositions } = this.props.state || {};
            if (rendererScrollPositions) {
                const renderer = this.rootRef.el.querySelector(".o_list_renderer");
                renderer.scrollLeft = rendererScrollPositions.left;
                renderer.scrollTop = rendererScrollPositions.top;
            }
        });

        this.archiveEnabled =
            "active" in this.props.fields
                ? !this.props.fields.active.readonly
                : "x_active" in this.props.fields
                ? !this.props.fields.x_active.readonly
                : false;
        useSubEnv({ model: this.model }); // do this in useModel?
        useViewButtons(this.model, this.rootRef, {
            beforeExecuteAction: this.beforeExecuteActionButton.bind(this),
            afterExecuteAction: this.afterExecuteActionButton.bind(this),
        });
        useSetupView({
            rootRef: this.rootRef,
            beforeLeave: async () => {
                const list = this.model.root;
                const editedRecord = list.editedRecord;
                if (editedRecord) {
                    if (!(await list.unselectRecord(true))) {
                        return false;
                    }
                }
            },
            beforeUnload: async (ev) => {
                const editedRecord = this.model.root.editedRecord;
                if (editedRecord) {
                    const isValid = await editedRecord.urgentSave();
                    if (!isValid) {
                        ev.preventDefault();
                        ev.returnValue = "Unsaved changes";
                    }
                }
            },
            getLocalState: () => {
                const renderer = this.rootRef.el.querySelector(".o_list_renderer");
                return {
                    rootState: this.model.root.exportState(),
                    rendererScrollPositions: { left: renderer.scrollLeft, top: renderer.scrollTop },
                };
            },
            getOrderBy: () => {
                return this.model.root.orderBy;
            },
        });

        usePager(() => {
            const list = this.model.root;
            const { count, hasLimitedCount, isGrouped, limit, offset } = list;
            return {
                offset: offset,
                limit: limit,
                total: count,
                onUpdate: async ({ offset, limit }, hasNavigated) => {
                    if (this.model.root.editedRecord) {
                        if (!(await this.model.root.editedRecord.save())) {
                            return;
                        }
                    }
                    await list.load({ limit, offset });
                    this.render(true); // FIXME WOWL reactivity
                    if (hasNavigated) {
                        this.onPageChangeScroll();
                    }
                },
                updateTotal: !isGrouped && hasLimitedCount ? () => list.fetchCount() : undefined,
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
        this.searchBarToggler = useSearchBarToggler();
        this.firstLoad = true;
        onWillPatch(() => {
            this.firstLoad = false;
        });
        useBus(this.env.searchModel, 'direct-export-data', this.onDirectExportData.bind(this));
    }

    get modelParams() {
        const { rootState } = this.props.state || {};
        const { defaultGroupBy, rawExpand } = this.archInfo;
        return {
            resModel: this.props.resModel,
            fields: { ...this.props.fields },
            activeFields: this.archInfo.activeFields,
            handleField: this.archInfo.handleField,
            viewMode: "list",
            groupByInfo: this.archInfo.groupBy.fields,
            limit: this.archInfo.limit || this.props.limit,
            countLimit: this.archInfo.countLimit,
            defaultOrder: this.archInfo.defaultOrder,
            defaultGroupBy: this.props.searchMenuTypes.includes("groupBy") ? defaultGroupBy : false,
            expand: rawExpand ? evaluateExpr(rawExpand, this.props.context) : false,
            groupsLimit: this.archInfo.groupsLimit,
            multiEdit: this.archInfo.multiEdit,
            rootState,
            onRecordSaved: this.onRecordSaved.bind(this),
            onWillSaveRecord: this.onWillSaveRecord.bind(this),
            onWillSaveMultiRecords: this.onWillSaveMultiRecords.bind(this),
            onSavedMultiRecords: this.onSavedMultiRecords.bind(this),
            onWillSetInvalidField: this.onWillSetInvalidField.bind(this),
        };
    }

    /**
     * onRecordSaved is a callBack that will be executed after the save
     * if it was done. It will therefore not be executed if the record
     * is invalid or if a server error is thrown.
     * @param {Record} record
     */
    async onRecordSaved(record) {}

    /**
     * onWillSaveRecord is a callBack that will be executed before the
     * record save if the record is valid if the record is valid.
     * If it returns false, it will prevent the save.
     * @param {Record} record
     */
    async onWillSaveRecord(record) {}

    async createRecord({ group } = {}) {
        const list = (group && group.list) || this.model.root;
        if (this.editable && !list.isGrouped) {
            if (!(list instanceof DynamicRecordList)) {
                throw new Error("List should be a DynamicRecordList");
            }
            if (list.editedRecord) {
                await list.editedRecord.save();
            }
            if (!list.editedRecord) {
                await (group || list).createRecord({}, this.editable === "top");
            }
            this.render();
        } else {
            await this.props.createRecord();
        }
    }

    async openRecord(record) {
        if (this.archInfo.openAction) {
            this.actionService.doActionButton({
                name: this.archInfo.openAction.action,
                type: this.archInfo.openAction.type,
                resModel: record.resModel,
                resId: record.resId,
                resIds: record.resIds,
                context: record.context,
                onClose: async () => {
                    await record.model.root.load();
                    record.model.notify();
                },
            });
        } else {
            const activeIds = this.model.root.records.map((datapoint) => datapoint.resId);
            this.props.selectRecord(record.resId, { activeIds });
        }
    }

    onClickCreate() {
        this.createRecord();
    }

    onClickDiscard() {
        const editedRecord = this.model.root.editedRecord;
        if (editedRecord.isNew) {
            this.model.root.removeRecord(editedRecord);
        } else {
            editedRecord.discard();
        }
    }

    onClickSave() {
        this.model.root.editedRecord.save();
    }

    onMouseDownDiscard(mouseDownEvent) {
        this.hasMousedownDiscard = true;
        document.addEventListener(
            "mouseup",
            (mouseUpEvent) => {
                this.hasMousedownDiscard = false;
                if (mouseUpEvent.target !== mouseDownEvent.target) {
                    if (this.nextActionAfterMouseup) {
                        this.nextActionAfterMouseup();
                    }
                }
                this.nextActionAfterMouseup = null;
            },
            { capture: true, once: true }
        );
    }

    onPageChangeScroll() {
        if (this.rootRef && this.rootRef.el) {
            this.rootRef.el.querySelector(".o_content").scrollTop = 0;
        }
    }

    getSelectedResIds() {
        return this.model.root.getResIds(true);
    }

    getStaticActionMenuItems() {
        const list = this.model.root;
        const isM2MGrouped = list.groupBy.some((groupBy) => {
            const fieldName = groupBy.split(":")[0];
            return list.fields[fieldName].type === "many2many";
        });
        return {
            export: {
                isAvailable: () => this.isExportEnable,
                sequence: 10,
                icon: "fa fa-upload",
                description: this.env._t("Export"),
                callback: () => this.onExportData(),
            },
            archive: {
                isAvailable: () => this.archiveEnabled && !isM2MGrouped,
                sequence: 20,
                icon: "oi oi-archive",
                description: this.env._t("Archive"),
                callback: () => {
                    this.dialogService.add(ConfirmationDialog, this.archiveDialogProps);
                },
            },
            unarchive: {
                isAvailable: () => this.archiveEnabled && !isM2MGrouped,
                sequence: 30,
                icon: "oi oi-unarchive",
                description: this.env._t("Unarchive"),
                callback: () => this.toggleArchiveState(false),
            },
            delete: {
                isAvailable: () => this.activeActions.delete && !isM2MGrouped,
                sequence: 40,
                icon: "fa fa-trash-o",
                description: this.env._t("Delete"),
                callback: () => this.onDeleteSelectedRecords(),
            },
        };
    }

    get archiveDialogProps() {
        return {
            body: this.env._t("Are you sure that you want to archive all the selected records?"),
            confirmLabel: this.env._t("Archive"),
            confirm: () => {
                this.toggleArchiveState(true);
            },
            cancel: () => {},
        };
    }

    get actionMenuItems() {
        const { actionMenus } = this.props.info;
        const staticActionItems = Object.entries(this.getStaticActionMenuItems())
            .filter(([key, item]) => item.isAvailable === undefined || item.isAvailable())
            .sort(([k1, item1], [k2, item2]) => (item1.sequence || 0) - (item2.sequence || 0))
            .map(([key, item]) =>
                Object.assign(
                    { key, groupNumber: STATIC_ACTIONS_GROUP_NUMBER },
                    omit(item, "isAvailable")
                )
            );

        return {
            action: [...staticActionItems, ...(actionMenus.action || [])],
            print: actionMenus.print,
        };
    }

    async onSelectDomain() {
        this.model.root.selectDomain(true);
        if (this.props.onSelectionChanged) {
            const resIds = await this.model.root.getResIds(true);
            this.props.onSelectionChanged(resIds);
        }
    }

    onUnselectAll() {
        this.model.root.selection.forEach((record) => {
            record.toggleSelection(false);
        });
        this.model.root.selectDomain(false);
    }

    get className() {
        return this.props.className;
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
        const list = this.model.root;
        return list.isGrouped ? list.nbTotalRecords : list.count;
    }

    get defaultExportList() {
        return unique(
            this.props.archInfo.columns
                .filter((col) => col.type === "field")
                .map((col) => this.props.fields[col.name])
                .filter((field) => field.exportable !== false)
        );
    }

    get display() {
        const { controlPanel } = this.props.display;
        if (!controlPanel) {
            return this.props.display;
        }
        return {
            ...this.props.display,
            controlPanel: {
                ...controlPanel,
                layoutActions: !this.nbSelected,
            },
        };
    }

    async downloadExport(fields, import_compat, format) {
        let ids = false;
        if (!this.isDomainSelected) {
            const resIds = await this.getSelectedResIds();
            ids = resIds.length > 0 && resIds;
        }
        const exportedFields = fields.map((field) => ({
            name: field.name || field.id,
            label: field.label || field.string,
            store: field.store,
            type: field.field_type || field.type,
        }));
        if (import_compat) {
            exportedFields.unshift({ name: "id", label: this.env._t("External ID") });
        }
        await download({
            data: {
                data: JSON.stringify({
                    import_compat,
                    context: this.props.context,
                    domain: this.model.root.domain,
                    fields: exportedFields,
                    groupby: this.model.root.groupBy,
                    ids,
                    model: this.model.root.resModel,
                }),
            },
            url: `/web/export/${format}`,
        });
    }

    async getExportedFields(model, import_compat, parentParams) {
        return await this.rpc("/web/export/get_fields", {
            ...parentParams,
            model,
            import_compat,
        });
    }

    /**
     * Opens the Export Dialog
     *
     * @private
     */
    async onExportData() {
        const dialogProps = {
            context: this.props.context,
            defaultExportList: this.defaultExportList,
            download: this.downloadExport.bind(this),
            getExportedFields: this.getExportedFields.bind(this),
            root: this.model.root,
        };
        this.dialogService.add(ExportDataDialog, dialogProps);
    }
    /**
     * Export Records in a xls file
     *
     * @private
     */
    async onDirectExportData() {
        await this.downloadExport(this.defaultExportList, false, "xlsx");
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
                        "Of the %s records selected, only the first %s have been archived/unarchived."
                    ),
                    resIds.length,
                    total
                ),
                { title: this.env._t("Warning") }
            );
        }
    }

    get deleteConfirmationDialogProps() {
        const root = this.model.root;
        const body =
            root.isDomainSelected || root.selection.length > 1
                ? this.env._t("Are you sure you want to delete these records?")
                : this.env._t("Are you sure you want to delete this record?");
        return {
            body,
            confirm: async () => {
                const total = root.count;
                const resIds = await this.model.root.deleteRecords();
                this.model.notify();
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
            confirmLabel: this.env._t("Delete"),
            cancel: () => {},
        };
    }

    async onDeleteSelectedRecords() {
        this.dialogService.add(ConfirmationDialog, this.deleteConfirmationDialogProps);
    }

    discardSelection() {
        this.model.root.records.forEach((record) => {
            record.toggleSelection(false);
        });
    }

    async beforeExecuteActionButton(clickParams) {
        if (clickParams.special !== "cancel" && this.model.root.editedRecord) {
            return this.model.root.editedRecord.save();
        }
    }

    async afterExecuteActionButton(clickParams) {}

    onWillSaveMultiRecords(editedRecord, validSelectedRecords) {
        if (this.hasMousedownDiscard) {
            this.nextActionAfterMouseup = () => this.model.root.multiSave(editedRecord);
            return false;
        }
        if (validSelectedRecords.length > 1) {
            const { isDomainSelected, selection } = this.model.root;
            return new Promise((resolve) => {
                const dialogProps = {
                    confirm: () => resolve(true),
                    cancel: () => {
                        editedRecord.discard();
                        resolve(false);
                    },
                    isDomainSelected,
                    fields: Object.keys(editedRecord.getChanges()).map((fieldName) => {
                        const activeField = editedRecord.activeFields[fieldName];
                        return {
                            name: fieldName,
                            label: activeField.string || editedRecord.fields[fieldName].string,
                            widget: activeField.widget,
                        };
                    }),
                    nbRecords: selection.length,
                    nbValidRecords: validSelectedRecords.length,
                    record: editedRecord,
                    fieldNodes: this.archInfo.fieldNodes,
                };

                const focusedCellBeforeDialog = document.activeElement.closest(".o_data_cell");
                this.dialogService.add(ListConfirmationDialog, dialogProps, {
                    onClose: () => {
                        if (focusedCellBeforeDialog) {
                            focusedCellBeforeDialog.focus();
                        }
                        editedRecord.discard();
                        resolve(false);
                    },
                });
            });
        }
        return true;
    }

    onWillSetInvalidField(record, fieldName) {
        if (this.hasMousedownDiscard) {
            this.nextActionAfterMouseup = () => record.setInvalidField(fieldName);
            return false;
        }
        return true;
    }

    onSavedMultiRecords(records) {
        records.forEach((record) => {
            record.selected = false;
        });
    }
}

ListController.template = `web.ListView`;
ListController.components = {
    ActionMenus,
    Layout,
    ViewButton,
    MultiRecordViewButton,
    SearchBar,
    CogMenu,
};
ListController.props = {
    ...standardViewProps,
    allowSelectors: { type: Boolean, optional: true },
    editable: { type: Boolean, optional: true },
    onSelectionChanged: { type: Function, optional: true },
    showButtons: { type: Boolean, optional: true },
    Model: Function,
    Renderer: Function,
    buttonTemplate: String,
    archInfo: Object,
};
ListController.defaultProps = {
    allowSelectors: true,
    createRecord: () => {},
    editable: true,
    selectRecord: () => {},
    showButtons: true,
};
