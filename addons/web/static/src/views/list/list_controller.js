import { _t } from "@web/core/l10n/translation";
import {
    deleteConfirmationMessage,
    ConfirmationDialog,
} from "@web/core/confirmation_dialog/confirmation_dialog";
import { download } from "@web/core/network/download";
import { rpc } from "@web/core/network/rpc";
import { evaluateExpr, evaluateBooleanExpr } from "@web/core/py_js/py";
import { user } from "@web/core/user";
import { unique } from "@web/core/utils/arrays";
import { useService, useBus } from "@web/core/utils/hooks";
import { omit } from "@web/core/utils/objects";
import { useSetupAction } from "@web/search/action_hook";
import { ActionMenus, STATIC_ACTIONS_GROUP_NUMBER } from "@web/search/action_menus/action_menus";
import { Layout } from "@web/search/layout";
import { usePager } from "@web/search/pager_hook";
import { useModelWithSampleData } from "@web/model/model";
import { DynamicRecordList } from "@web/model/relational_model/dynamic_record_list";
import { extractFieldsFromArchInfo } from "@web/model/relational_model/utils";
import { standardViewProps } from "@web/views/standard_view_props";
import { MultiRecordViewButton } from "@web/views/view_button/multi_record_view_button";
import { ViewButton } from "@web/views/view_button/view_button";
import { executeButtonCallback, useViewButtons } from "@web/views/view_button/view_button_hook";
import { ExportDataDialog } from "@web/views/view_dialogs/export_data_dialog";
import { ListConfirmationDialog } from "./list_confirmation_dialog";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { useSearchBarToggler } from "@web/search/search_bar/search_bar_toggler";
import { session } from "@web/session";
import { ListCogMenu } from "./list_cog_menu";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

import {
    Component,
    onMounted,
    onWillPatch,
    onWillRender,
    onWillStart,
    useEffect,
    useRef,
    useState,
    useSubEnv,
} from "@odoo/owl";

// -----------------------------------------------------------------------------

export class ListController extends Component {
    static template = `web.ListView`;
    static components = {
        ActionMenus,
        Layout,
        ViewButton,
        MultiRecordViewButton,
        SearchBar,
        CogMenu: ListCogMenu,
        DropdownItem,
    };
    static props = {
        ...standardViewProps,
        allowSelectors: { type: Boolean, optional: true },
        onSelectionChanged: { type: Function, optional: true },
        readonly: { type: Boolean, optional: true },
        showButtons: { type: Boolean, optional: true },
        Model: Function,
        Renderer: Function,
        buttonTemplate: String,
        archInfo: Object,
    };
    static defaultProps = {
        allowSelectors: true,
        createRecord: () => {},
        selectRecord: () => {},
        showButtons: true,
    };

    setup() {
        this.actionService = useService("action");
        this.dialogService = useService("dialog");
        this.rootRef = useRef("root");

        this.archInfo = this.props.archInfo;
        this.activeActions = this.archInfo.activeActions;
        this.onOpenFormView = this.openRecord.bind(this);
        this.editable = (!this.props.readonly && this.archInfo.editable) || false;
        this.hasOpenFormViewButton = this.editable ? this.archInfo.openFormView : false;
        this.model = useState(useModelWithSampleData(this.props.Model, this.modelParams));

        // In multi edition, we save or notify invalidity directly when a field is updated, which
        // occurs on the change event for input fields. But we don't want to do it when clicking on
        // "Discard". So we set a flag on mousedown (which triggers the update) to block the multi
        // save or invalid notification.
        // However, if the mouseup (and click) is done outside "Discard", we finally want to do it.
        // We use `nextActionAfterMouseup` for this purpose: it registers a callback to execute if
        // the mouseup following a mousedown on "Discard" isn't done on "Discard".
        this.hasMousedownDiscard = false;
        this.nextActionAfterMouseup = null;

        this.optionalActiveFields = {};

        this.editedRecord = null;
        onWillRender(() => {
            this.editedRecord = this.model.root.editedRecord;
        });

        onWillStart(async () => {
            this.isExportEnable = await user.hasGroup("base.group_allow_export");
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
        useSubEnv({ model: this.model }); // do this in useModelWithSampleData?
        useViewButtons(this.rootRef, {
            beforeExecuteAction: this.beforeExecuteActionButton.bind(this),
            afterExecuteAction: this.afterExecuteActionButton.bind(this),
            reload: () => this.model.load(),
        });
        useSetupAction({
            rootRef: this.rootRef,
            beforeLeave: async () => this.model.root.leaveEditMode(),
            beforeUnload: async (ev) => {
                if (this.editedRecord) {
                    const isValid = await this.editedRecord.urgentSave();
                    if (!isValid) {
                        ev.preventDefault();
                        ev.returnValue = "Unsaved changes";
                    }
                }
            },
            getLocalState: () => {
                const renderer = this.rootRef.el.querySelector(".o_list_renderer");
                return {
                    modelState: this.model.exportState(),
                    rendererScrollPositions: {
                        left: renderer.scrollLeft,
                        top: renderer.scrollTop,
                    },
                };
            },
            getOrderBy: () => this.model.root.orderBy,
        });

        usePager(() => {
            const { count, hasLimitedCount, isGrouped, limit, offset } = this.model.root;
            return {
                offset: offset,
                limit: limit,
                total: count,
                onUpdate: async ({ offset, limit }, hasNavigated) => {
                    if (this.editedRecord) {
                        if (!(await this.editedRecord.save())) {
                            return;
                        }
                    }
                    await this.model.root.load({ limit, offset });
                    if (hasNavigated) {
                        this.onPageChangeScroll();
                    }
                },
                updateTotal:
                    !isGrouped && hasLimitedCount ? () => this.model.root.fetchCount() : undefined,
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
        useBus(this.env.searchModel, "direct-export-data", this.onDirectExportData.bind(this));
    }

    get modelParams() {
        const { rawExpand } = this.archInfo;
        const { activeFields, fields } = extractFieldsFromArchInfo(
            this.archInfo,
            this.props.fields
        );
        const groupByInfo = {};
        for (const fieldName in this.archInfo.groupBy.fields) {
            const fieldNodes = this.archInfo.groupBy.fields[fieldName].fieldNodes;
            const fields = this.archInfo.groupBy.fields[fieldName].fields;
            groupByInfo[fieldName] = extractFieldsFromArchInfo({ fieldNodes }, fields);
        }

        const modelConfig = this.props.state?.modelState?.config || {
            resModel: this.props.resModel,
            fields,
            activeFields,
            openGroupsByDefault: rawExpand ? evaluateExpr(rawExpand, this.props.context) : false,
        };

        return {
            config: modelConfig,
            state: this.props.state?.modelState,
            groupByInfo,
            limit: this.archInfo.limit || this.props.limit,
            countLimit: this.archInfo.countLimit,
            defaultOrderBy: this.archInfo.defaultOrder,
            groupsLimit: this.archInfo.groupsLimit,
            multiEdit: this.archInfo.multiEdit,
            activeIdsLimit: session.active_ids_limit,
            hooks: {
                onRecordSaved: this.onRecordSaved.bind(this),
                onWillSaveRecord: this.onWillSaveRecord.bind(this),
                onWillSaveMulti: this.onWillSaveMulti.bind(this),
                onWillSetInvalidField: this.onWillSetInvalidField.bind(this),
            },
        };
    }

    get actionMenuProps() {
        return {
            getActiveIds: () => this.model.root.selection.map((r) => r.resId),
            context: this.props.context,
            domain: this.props.domain,
            items: this.actionMenuItems,
            isDomainSelected: this.model.root.isDomainSelected,
            resModel: this.model.root.resModel,
            onActionExecuted: () => this.model.load(),
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
            await list.leaveEditMode();
            if (!list.editedRecord) {
                await (group || list).addNewRecord(this.editable === "top");
            }
            this.render();
        } else {
            await this.props.createRecord();
        }
    }

    async openRecord(record, { force, newWindow } = { force: false }) {
        const dirty = await record.isDirty();
        if (dirty) {
            await record.save();
        }
        if (this.archInfo.openAction) {
            this.actionService.doActionButton(
                {
                    name: this.archInfo.openAction.action,
                    type: this.archInfo.openAction.type,
                    resModel: record.resModel,
                    resId: record.resId,
                    resIds: record.resIds,
                    context: record.context,
                    onClose: async () => {
                        await record.model.root.load();
                    },
                },
                {
                    newWindow,
                }
            );
        } else {
            const activeIds = this.model.root.records.map((datapoint) => datapoint.resId);
            this.props.selectRecord(record.resId, { activeIds, force, newWindow });
        }
    }

    async onClickCreate() {
        return executeButtonCallback(this.rootRef.el, () => this.createRecord());
    }

    async onClickDiscard() {
        return executeButtonCallback(this.rootRef.el, () =>
            this.model.root.leaveEditMode({ discard: true })
        );
    }

    async onClickSave() {
        return executeButtonCallback(this.rootRef.el, async () => {
            const saved = await this.editedRecord.save();
            if (saved) {
                await this.model.root.leaveEditMode();
            }
        });
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
            if (this.env.isSmall) {
                this.rootRef.el.scrollTop = 0;
            } else {
                this.rootRef.el.querySelector(".o_content .o_list_renderer").scrollTop = 0;
            }
        }
    }

    getSelectedResIds() {
        return this.model.root.getResIds(true);
    }

    getStaticActionMenuItems() {
        return {
            export: {
                isAvailable: () => this.isExportEnable,
                sequence: 10,
                icon: "fa fa-upload",
                description: _t("Export"),
                callback: () => this.onExportData(),
            },
            archive: {
                isAvailable: () => this.archiveEnabled,
                sequence: 20,
                icon: "oi oi-archive",
                description: _t("Archive"),
                callback: () => {
                    this.dialogService.add(ConfirmationDialog, this.archiveDialogProps);
                },
            },
            unarchive: {
                isAvailable: () => this.archiveEnabled,
                sequence: 30,
                icon: "oi oi-unarchive",
                description: _t("Unarchive"),
                callback: () => this.toggleArchiveState(false),
            },
            duplicate: {
                isAvailable: () => this.activeActions.duplicate,
                sequence: 35,
                icon: "fa fa-clone",
                description: _t("Duplicate"),
                callback: () => this.duplicateRecords(),
            },
            delete: {
                isAvailable: () => this.activeActions.delete,
                sequence: 40,
                icon: "fa fa-trash-o",
                description: _t("Delete"),
                callback: () => this.onDeleteSelectedRecords(),
            },
        };
    }

    get archiveDialogProps() {
        return {
            body: _t("Are you sure that you want to archive all the selected records?"),
            confirmLabel: _t("Archive"),
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
            action: [...staticActionItems, ...(actionMenus?.action || [])],
            print: actionMenus?.print,
        };
    }

    async onSelectDomain() {
        await this.model.root.selectDomain(true);
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

    evalViewModifier(modifier) {
        return evaluateBooleanExpr(modifier, this.model.root.evalContext);
    }

    get className() {
        return this.props.className;
    }

    get hasSelectedRecords() {
        return this.nbSelected || this.isDomainSelected;
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
        return list.isGrouped ? list.recordCount : list.count;
    }

    get defaultExportList() {
        return unique(
            this.props.archInfo.columns
                .filter((col) => col.type === "field")
                .filter((col) => !col.optional || this.optionalActiveFields[col.name])
                .filter((col) => !evaluateBooleanExpr(col.column_invisible, this.props.context))
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
                layoutActions: !this.hasSelectedRecords,
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
            exportedFields.unshift({
                name: "id",
                label: _t("External ID"),
            });
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
        let domain = this.model.root.domain;
        if (!this.isDomainSelected) {
            const resIds = await this.getSelectedResIds();
            const ids = resIds.length > 0 && resIds;
            domain = [["id", "in", ids]];
        }
        return await rpc("/web/export/get_fields", {
            ...parentParams,
            model,
            domain,
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
        if (archive) {
            return this.model.root.archive(true);
        }
        return this.model.root.unarchive(true);
    }

    async duplicateRecords() {
        return this.model.root.duplicateRecords();
    }

    get deleteConfirmationDialogProps() {
        const root = this.model.root;
        let body = deleteConfirmationMessage;
        if (root.isDomainSelected || root.selection.length > 1) {
            body = _t("Are you sure you want to delete these records?");
        }
        return {
            title: _t("Bye-bye, record!"),
            body,
            confirmLabel: _t("Delete"),
            confirm: () => this.model.root.deleteRecords(),
            cancel: () => {},
            cancelLabel: _t("No, keep it"),
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
        if (clickParams.special !== "cancel" && this.editedRecord) {
            return this.editedRecord.save();
        }
    }

    async afterExecuteActionButton(clickParams) {}

    onWillSaveMulti(editedRecord, changes, validSelectedRecords) {
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
                        if (this.editedRecord) {
                            this.model.root.leaveEditMode({ discard: true });
                        } else {
                            editedRecord.discard();
                        }
                        resolve(false);
                    },
                    isDomainSelected,
                    fields: Object.keys(changes).map((fieldName) => {
                        const fieldNode = Object.values(this.archInfo.fieldNodes).find(
                            (fieldNode) => fieldNode.name === fieldName
                        );
                        const label = fieldNode && fieldNode.string;
                        return {
                            name: fieldName,
                            label: label || editedRecord.fields[fieldName].string,
                            fieldNode,
                            widget: fieldNode && fieldNode.widget,
                        };
                    }),
                    nbRecords: selection.length,
                    nbValidRecords: validSelectedRecords.length,
                    record: editedRecord,
                };

                const focusedCellBeforeDialog = document.activeElement.closest(".o_data_cell");
                this.dialogService.add(ListConfirmationDialog, dialogProps, {
                    onClose: () => {
                        if (focusedCellBeforeDialog) {
                            focusedCellBeforeDialog.focus();
                        }
                        this.model.root.leaveEditMode({ discard: true });
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
}
