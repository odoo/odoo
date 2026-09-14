// @ts-check
/** @odoo-module native */

import { status, useEffect, useState } from "@odoo/owl";
import { DropdownItem } from "@web/components/dropdown/dropdown_item";
import { useSetupAction } from "@web/core/action_hook";
import { makeLogger } from "@web/core/debug/debug_logger";
import { evaluateBooleanExpr, evaluateExpr } from "@web/core/py_js/py";
import { useModelWithSampleData } from "@web/model/model";
import { extractFieldsFromArchInfo } from "@web/model/relational_model";
import { DynamicRecordList } from "@web/model/relational_model/dynamic_record_list";
import { ActionMenus } from "@web/search/action_menus/action_menus";
import { MultiRecordCogMenu } from "@web/views/multi_record_cog_menu";
import { MultiRecordController } from "@web/views/multi_record_controller";
import { standardViewProps } from "@web/views/standard_view_props";
import { MultiRecordViewButton } from "@web/views/view_button/multi_record_view_button";
import { ViewButton } from "@web/views/view_button/view_button";
import { executeButtonCallback } from "@web/views/view_button/view_button_hook";
import { SelectionBox } from "@web/views/view_components/selection_box";
import { ViewLayout } from "@web/views/view_components/view_layout";
import {
    exportableFields,
    getMultiRecordModelParams,
    getOpenActionParams,
    handleBeforeUnload,
} from "@web/views/view_utils";

import { ListConfirmationDialog } from "./list_confirmation_dialog.js";

const log = makeLogger("web.view.list");

export class ListController extends MultiRecordController {
    static template = `web.ListView`;
    static components = {
        ActionMenus,
        ViewLayout,
        ViewButton,
        MultiRecordViewButton,
        CogMenu: MultiRecordCogMenu,
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

    /** @type {Record<string, any>} */
    optionalActiveFields;

    /** @type {(() => void)[]} */
    nextActionsAfterMouseup;

    /** @override */
    setupModel() {
        this.activeActions = this.archInfo.activeActions;
        this.onOpenFormView = this.openRecord.bind(this);
        this.editable = (!this.props.readonly && this.archInfo.editable) || false;
        this.hasOpenFormViewButton = this.editable ? this.archInfo.openFormView : false;

        this.model = useState(
            useModelWithSampleData(
                this.props.Model,
                this.modelParams,
                /** @type {any} */ (this.modelOptions),
            ),
        );

        this.hasMousedownDiscard = false;
        this.nextActionsAfterMouseup = [];

        this.optionalActiveFields = useState({});
    }

    /** @override */
    setupInteractions() {
        const { setScrollFromState } = useSetupAction({
            rootRef: this.rootRef,
            beforeLeave: this.beforeLeave.bind(this),
            beforeUnload: this.beforeUnload.bind(this),
            getLocalState: () => {
                const renderer = this.rootRef.el?.querySelector(".o_list_renderer");
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

        useEffect(
            (isReady) => {
                if (isReady) {
                    if (this.env.isSmall) {
                        setScrollFromState();
                    } else {
                        const { rendererScrollPositions } = this.props.state || {};
                        if (rendererScrollPositions) {
                            const renderer = /** @type {HTMLElement} */ (
                                this.rootRef.el?.querySelector(".o_list_renderer")
                            );
                            renderer.scrollLeft = rendererScrollPositions.left;
                            renderer.scrollTop = rendererScrollPositions.top;
                        }
                    }
                }
            },
            () => [this.model.isReady],
        );

        this.setupPager();
    }

    /** @returns {Promise<boolean>} the edited row must be saved before the page moves */
    async beforePagerUpdate() {
        return this.editedRecord ? Boolean(await this.editedRecord.save()) : true;
    }

    /** @returns {Record<string, any>} */
    get modelParams() {
        const { rawExpand } = this.archInfo;
        const { activeFields, fields } = extractFieldsFromArchInfo(
            this.archInfo,
            this.props.fields,
        );
        const groupByInfo = {};
        for (const fieldName of Object.keys(this.archInfo.groupBy.fields)) {
            const fieldNodes = this.archInfo.groupBy.fields[fieldName].fieldNodes;
            const fields = this.archInfo.groupBy.fields[fieldName].fields;
            groupByInfo[fieldName] = extractFieldsFromArchInfo(
                /** @type {any} */ ({ fieldNodes }),
                fields,
            );
        }

        return getMultiRecordModelParams({
            archInfo: this.archInfo,
            props: this.props,
            uiHooks: this._uiHooks,
            config: {
                resModel: this.props.resModel,
                fields,
                activeFields,
                openGroupsByDefault: rawExpand
                    ? evaluateExpr(rawExpand, this.props.context)
                    : false,
            },
            hooks: {
                lifecycle: {
                    onRecordSaved: this.onRecordSaved.bind(this),
                    onWillSaveRecord: this.onWillSaveRecord.bind(this),
                    onWillSaveMulti: this.onWillSaveMulti.bind(this),
                    onAskMultiSaveConfirmation:
                        this.onAskMultiSaveConfirmation.bind(this),
                    onWillSetInvalidField: this.onWillSetInvalidField.bind(this),
                },
            },
            extras: {
                groupByInfo,
                limit: this.archInfo.limit || this.props.limit,
                groupsLimit: this.archInfo.groupsLimit,
                multiEdit: !this.props.readonly && this.archInfo.multiEdit,
                useSendBeaconToSaveUrgently: true,
            },
        });
    }

    get editedRecord() {
        return this.model.root.editedRecord;
    }

    get className() {
        return this.props.className;
    }

    /** @returns {any[]} */
    getExportableFields() {
        const { activeFields, fields } = this.model.root;
        const visibleColumns = new Set(
            this.props.archInfo.columns
                .filter((col) => col.type === "field")
                .filter(
                    (col) =>
                        !evaluateBooleanExpr(
                            col.column_invisible,
                            this.model.root.evalContext,
                        ),
                )
                .filter((col) => !col.optional || this.optionalActiveFields[col.name])
                .map((col) => col.name),
        );
        return exportableFields(fields, activeFields, (field) =>
            field.relatedPropertyField
                ? this.optionalActiveFields[field.name]
                : visibleColumns.has(field.name),
        );
    }

    /**
     * @param {Event} ev
     * @returns {Promise<any>}
     */
    async beforeLeave(ev) {
        return this.model.root.leaveEditMode();
    }

    /** @param {BeforeUnloadEvent} ev */
    beforeUnload(ev) {
        const record = this.editedRecord;
        return handleBeforeUnload(ev, {
            record,
            inDialog: this.env.inDialog,
            useSendBeacon: this.model.useSendBeaconToSaveUrgently,
            urgentSave: () => record.urgentSave(),
        });
    }

    /** @param {any} record */
    async onRecordSaved(record) {}

    /** @param {any} record */
    async onWillSaveRecord(record) {}

    /** @param {{ group?: any }} [options] */
    async createRecord({ group } = /** @type {any} */ ({})) {
        log.logic("createRecord", () => ({
            editable: this.editable,
            group: group?.value,
            ready: this.model.isReady,
        }));
        if (!this.model.isReady && !this.model.config.groupBy.length && this.editable) {
            await this.model.whenReady;
        }
        const list = group?.list || this.model.root;
        if (this.editable && !list.isGrouped) {
            if (!(list instanceof DynamicRecordList)) {
                throw new Error("List should be a DynamicRecordList");
            }
            await list.leaveEditMode();
            if (!list.editedRecord) {
                const position = this.editable;
                if (group) {
                    await group.addNewRecord({ position });
                } else {
                    await list.addNewRecord({ position });
                }
            }
            this.render();
        } else {
            await this.props.createRecord();
        }
    }

    /**
     * @param {any} record
     * @param {{ force?: boolean, newWindow?: boolean }} [options]
     */
    async openRecord(record, options = {}) {
        const { force = false, newWindow } = options;
        const dirty = await record.isDirty();
        log.logic("openRecord", () => ({
            resModel: record.resModel,
            resId: record.resId,
            dirty,
            force,
            newWindow,
            openAction: Boolean(this.archInfo.openAction),
        }));
        if (dirty && !(await record.save())) {
            return;
        }
        if (this.props.allowOpenAction && this.archInfo.openAction) {
            this.actionService.doActionButton(
                getOpenActionParams(this.archInfo.openAction, record),
                { newWindow },
            );
        } else {
            const activeIds = this.model.root.records.map(
                (datapoint) => datapoint.resId,
            );
            this.props.selectRecord(record.resId, {
                activeIds,
                force,
                newWindow,
            });
        }
    }

    async onClickCreate() {
        return executeButtonCallback(/** @type {HTMLElement} */ (this.rootRef.el), () =>
            this.createRecord(),
        );
    }

    async onClickDiscard() {
        return executeButtonCallback(/** @type {HTMLElement} */ (this.rootRef.el), () =>
            this.model.root.leaveEditMode({ discard: true }),
        );
    }

    async onClickSave() {
        return executeButtonCallback(
            /** @type {HTMLElement} */ (this.rootRef.el),
            async () => {
                const saved = await this.editedRecord.save();
                if (saved) {
                    await this.model.root.leaveEditMode();
                }
            },
        );
    }

    /** @param {MouseEvent} mouseDownEvent */
    onMouseDownDiscard(mouseDownEvent) {
        this.hasMousedownDiscard = true;
        document.addEventListener(
            "mouseup",
            (mouseUpEvent) => {
                this.hasMousedownDiscard = false;
                if (status(this) === "destroyed") {
                    this.nextActionsAfterMouseup = [];
                    return;
                }
                if (mouseUpEvent.target !== mouseDownEvent.target) {
                    for (const action of this.nextActionsAfterMouseup) {
                        action();
                    }
                }
                this.nextActionsAfterMouseup = [];
            },
            { capture: true, once: true },
        );
    }

    get scrollSelector() {
        return ".o_content .o_list_renderer";
    }

    discardSelection() {
        this.model.root.records.forEach((record) => {
            record.toggleSelection(false);
        });
    }

    /**
     * @param {{ special?: string }} clickParams
     * @returns {Promise<boolean | undefined>}
     */
    async beforeExecuteActionButton(clickParams) {
        if (clickParams.special !== "cancel" && this.editedRecord) {
            return this.editedRecord.save();
        }
    }

    /**
     * @param {Record<string, any>} changes
     * @param {any[]} validSelectedRecords
     * @returns {Promise<boolean> | boolean}
     */
    onAskMultiSaveConfirmation(changes, validSelectedRecords) {
        if (this.model.root.selection.length > 1 && validSelectedRecords.length) {
            const record = validSelectedRecords[0];
            const { isDomainSelected, selection } = this.model.root;
            return new Promise((resolve) => {
                const dialogProps = {
                    confirm: () => resolve(true),
                    cancel: () => resolve(false),
                    isDomainSelected,
                    fields: Object.keys(changes).map((fieldName) => {
                        const fieldNode = Object.values(this.archInfo.fieldNodes).find(
                            (fieldNode) => fieldNode.name === fieldName,
                        );
                        const label = fieldNode?.string;
                        return {
                            name: fieldName,
                            label: label || record.fields[fieldName].string,
                            fieldNode,
                            widget: fieldNode?.widget,
                        };
                    }),
                    changes,
                    nbRecords: selection.length,
                    nbValidRecords: validSelectedRecords.length,
                    record,
                };

                const focusedCellBeforeDialog = /** @type {HTMLElement | null} */ (
                    document.activeElement?.closest(".o_data_cell")
                );
                this.dialogService.add(ListConfirmationDialog, dialogProps, {
                    onClose: () => {
                        if (focusedCellBeforeDialog?.isConnected) {
                            focusedCellBeforeDialog.focus();
                        }
                        resolve(false);
                    },
                });
            });
        }
        return true;
    }

    /**
     * @param {any} editedRecord
     * @param {Record<string, any>} changes
     * @returns {boolean}
     */
    onWillSaveMulti(editedRecord, changes) {
        log.logic("onWillSaveMulti", () => ({
            fields: Object.keys(changes),
            deferred: this.hasMousedownDiscard,
        }));
        if (this.hasMousedownDiscard) {
            this.nextActionsAfterMouseup.push(() =>
                this.model.root.multiSave(editedRecord, changes),
            );
            return false;
        }
        return true;
    }

    /**
     * @param {any} record
     * @param {string} fieldName
     * @returns {boolean}
     */
    onWillSetInvalidField(record, fieldName) {
        if (this.hasMousedownDiscard) {
            this.nextActionsAfterMouseup.push(() => record.setInvalidField(fieldName));
            return false;
        }
        return true;
    }
}
