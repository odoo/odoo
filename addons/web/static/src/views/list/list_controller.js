import { _t } from "@web/core/l10n/translation";
import { evaluateExpr, evaluateBooleanExpr } from "@web/core/py_js/py";
import { user } from "@web/core/user";
import { unique } from "@web/core/utils/arrays";
import { useService } from "@web/core/utils/hooks";
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
import { ListConfirmationDialog } from "./list_confirmation_dialog";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { useSearchBarToggler } from "@web/search/search_bar/search_bar_toggler";
import { session } from "@web/session";
import { ListCogMenu } from "./list_cog_menu";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { SelectionBox } from "@web/views/view_components/selection_box";
import { useExportRecords, useDeleteRecords } from "@web/views/view_hook";

import {
    Component,
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
        SelectionBox,
    };
    static props = {
        ...standardViewProps,
        allowSelectors: { type: Boolean, optional: true },
        onSelectionChanged: { type: Function, optional: true },
        readonly: { type: Boolean, optional: true },
        showButtons: { type: Boolean, optional: true },
        allowOpenAction: { type: Boolean, optional: true },
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
        allowOpenAction: true,
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
        this.model = useState(
            useModelWithSampleData(this.props.Model, this.modelParams, this.modelOptions)
        );

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

        let { rendererScrollPositions } = this.props.state || {};
        useEffect(() => {
            if (rendererScrollPositions) {
                const renderer = this.rootRef.el.querySelector(".o_list_renderer");
                if (renderer) {
                    renderer.scrollLeft = rendererScrollPositions.left;
                    renderer.scrollTop = rendererScrollPositions.top;
                    rendererScrollPositions = null;
                }
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
                        left: renderer?.scrollLeft || 0,
                        top: renderer?.scrollTop || 0,
                    },
                };
            },
            getOrderBy: () => this.model.root.orderBy,
        });

        usePager(() => {
            if (this.model.useSampleModel) {
                return;
            }
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
                this.onSelectionChanged();
            },
            () => [this.model.root.selection.length, this.model.root.isDomainSelected]
        );
        this.searchBarToggler = useSearchBarToggler();
        this.firstLoad = true;
        onWillPatch(() => {
            this.firstLoad = false;
        });
        this.exportRecords = useExportRecords(this.env, this.props.context, () =>
            this.getExportableFields()
        );
        this.deleteRecordsWithConfirmation = useDeleteRecords(this.model);
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

    get modelOptions() {
        return {
            lazy:
                !this.env.config.isReloadingController &&
                !this.env.inDialog &&
                !!this.props.display.controlPanel,
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
            onActionExecuted: ({ noReload } = {}) => {
                if (!noReload) {
                    return this.model.load();
                }
            },
        };
    }

    get archiveDialogProps() {
        return {};
    }

    get deleteConfirmationDialogProps() {
        return {};
    }

    getExportableFields() {
        return unique(
            this.props.archInfo.columns
                .filter((col) => col.type === "field")
                .filter((col) => !col.optional || this.optionalActiveFields[col.name])
                .filter((col) => !evaluateBooleanExpr(col.column_invisible, this.props.context))
                .map((col) => this.props.fields[col.name])
                .filter((field) => field.exportable !== false)
        );
    }

    onDeleteSelectedRecords() {
        this.deleteRecordsWithConfirmation(this.deleteConfirmationDialogProps);
    }

    /**
     * onRecordSaved is a callBack that will be executed after the save
     * if it was done. It will therefore not be executed if the record
     * is invalid or if a server error is thrown.
     * @param {Record} record
     */
    async onRecordSaved(record) {}

    async onSelectionChanged() {
        if (this.props.onSelectionChanged) {
            const resIds = await this.model.root.getResIds(true);
            this.props.onSelectionChanged(resIds);
        }
    }

    /**
     * onWillSaveRecord is a callBack that will be executed before the
     * record save if the record is valid if the record is valid.
     * If it returns false, it will prevent the save.
     * @param {Record} record
     */
    async onWillSaveRecord(record) {}

    async createRecord({ group } = {}) {
        if (!this.model.isReady && !this.model.config.groupBy.length && this.editable) {
            // If the view isn't grouped and the list is editable, a new record row will be added,
            // in edition. In this situation, we must wait for the model to be ready.
            await this.model.whenReady;
        }
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
        if (this.props.allowOpenAction && this.archInfo.openAction) {
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

    getStaticActionMenuItems() {
        return {
            export: {
                isAvailable: () => this.isExportEnable,
                sequence: 10,
                icon: "fa fa-upload",
                description: _t("Export"),
                callback: () => this.exportRecords(),
            },
            duplicate: {
                isAvailable: () => this.activeActions.duplicate,
                sequence: 30,
                icon: "fa fa-clone",
                description: _t("Duplicate"),
                callback: () => this.model.root.duplicateRecords(),
            },
            archive: {
                isAvailable: () => this.archiveEnabled,
                sequence: 40,
                icon: "oi oi-archive",
                description: _t("Archive"),
                callback: () =>
                    this.model.root.toggleArchiveWithConfirmation(true, this.archiveDialogProps),
            },
            unarchive: {
                isAvailable: () => this.archiveEnabled,
                sequence: 45,
                icon: "oi oi-unarchive",
                description: _t("Unarchive"),
                callback: () => this.model.root.toggleArchiveWithConfirmation(false),
            },
            delete: {
                isAvailable: () => this.activeActions.delete,
                sequence: 50,
                icon: "fa fa-trash-o",
                description: _t("Delete"),
                class: "text-danger",
                callback: () => this.onDeleteSelectedRecords(),
            },
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

    get hasSelectedRecords() {
        return this.model.root.selection.length || this.isDomainSelected;
    }

    get isDomainSelected() {
        return this.model.root.isDomainSelected;
    }

    evalViewModifier(modifier) {
        return evaluateBooleanExpr(modifier, this.model.root.evalContext);
    }

    get className() {
        return this.props.className;
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
