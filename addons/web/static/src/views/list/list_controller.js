// @ts-check

/** @module @web/views/list/list_controller - List view orchestrator: pagination, selection, inline editing, multi-edit, and export */

import { onWillPatch, onWillRender, useEffect, useState } from "@odoo/owl";
import { DropdownItem } from "@web/components/dropdown/dropdown_item";
import { evaluateBooleanExpr, evaluateExpr } from "@web/core/py_js/py";
import { unique } from "@web/core/utils/collections/arrays";
import { useModelWithSampleData } from "@web/model/model";
import { DynamicRecordList } from "@web/model/relational_model/dynamic_record_list";
import { extractFieldsFromArchInfo } from "@web/model/relational_model/utils";
import { useSetupAction } from "@web/search/action_hook";
import { ActionMenus } from "@web/search/action_menus/action_menus";
import { Layout } from "@web/search/layout";
import { usePager } from "@web/search/pager_hook";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { session } from "@web/session";
import { MultiRecordController } from "@web/views/multi_record_controller";
import { standardViewProps } from "@web/views/standard_view_props";
import { MultiRecordViewButton } from "@web/views/view_button/multi_record_view_button";
import { ViewButton } from "@web/views/view_button/view_button";
import { executeButtonCallback } from "@web/views/view_button/view_button_hook";
import { SelectionBox } from "@web/views/view_components/selection_box";

import { ListCogMenu } from "./list_cog_menu";
import { ListConfirmationDialog } from "./list_confirmation_dialog";

// -----------------------------------------------------------------------------

/**
 * Controller for the list (tree) view.
 *
 * Extends {@link MultiRecordController} with list-specific behaviour: inline
 * editing, multi-edit confirmation, pager integration, record creation (inline
 * or form), optional fields toggling, and keyboard/mouse discard handling.
 */
export class ListController extends MultiRecordController {
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

    /**
     * Initialize list-specific state, model, pager, scroll restoration, and hooks.
     * @override
     */
    setup() {
        super.setup();

        // --- List-specific state ---
        this.activeActions = this.archInfo.activeActions;
        this.onOpenFormView = this.openRecord.bind(this);
        this.editable = (!this.props.readonly && this.archInfo.editable) || false;
        this.hasOpenFormViewButton = this.editable ? this.archInfo.openFormView : false;

        // --- Model ---
        this.model = useState(
            useModelWithSampleData(
                this.props.Model,
                this.modelParams,
                /** @type {any} */ (this.modelOptions),
            ),
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

        // --- Common post-model behavior ---
        this.initMultiRecordBehavior();

        // --- List-specific hooks ---
        const { setScrollFromState } = useSetupAction({
            rootRef: this.rootRef,
            beforeLeave: this.beforeLeave.bind(this),
            beforeUnload: this.beforeUnload.bind(this),
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

        useEffect(
            (isReady) => {
                if (isReady) {
                    if (this.env.isSmall) {
                        setScrollFromState();
                    } else {
                        const { rendererScrollPositions } = this.props.state || {};
                        if (rendererScrollPositions) {
                            const renderer =
                                this.rootRef.el.querySelector(".o_list_renderer");
                            renderer.scrollLeft = rendererScrollPositions.left;
                            renderer.scrollTop = rendererScrollPositions.top;
                        }
                    }
                }
            },
            () => [this.model.isReady],
        );

        usePager(() => {
            if (this.model.useSampleModel) {
                return;
            }
            const { count, hasLimitedCount, isGrouped, limit, offset } =
                this.model.root;
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
                    !isGrouped && hasLimitedCount
                        ? () => this.model.root.fetchCount()
                        : undefined,
            };
        });

        onWillPatch(() => {
            this.firstLoad = false;
        });
    }

    // -------------------------------------------------------------------------
    // Getters
    // -------------------------------------------------------------------------

    /**
     * Build the params object passed to the relational model constructor.
     *
     * Merges arch-extracted fields, groupBy info, limits, ordering, and
     * hook callbacks into a single configuration object.
     *
     * @returns {Record<string, any>}
     */
    get modelParams() {
        const { rawExpand } = this.archInfo;
        const { activeFields, fields } = extractFieldsFromArchInfo(
            this.archInfo,
            this.props.fields,
        );
        const groupByInfo = {};
        for (const fieldName in this.archInfo.groupBy.fields) {
            const fieldNodes = this.archInfo.groupBy.fields[fieldName].fieldNodes;
            const fields = this.archInfo.groupBy.fields[fieldName].fields;
            groupByInfo[fieldName] = extractFieldsFromArchInfo(
                /** @type {any} */ ({ fieldNodes }),
                fields,
            );
        }

        const modelConfig = this.props.state?.modelState?.config || {
            resModel: this.props.resModel,
            fields,
            activeFields,
            openGroupsByDefault: rawExpand
                ? evaluateExpr(rawExpand, this.props.context)
                : false,
        };

        return {
            config: modelConfig,
            state: this.props.state?.modelState,
            groupByInfo,
            limit: this.archInfo.limit || this.props.limit,
            countLimit: this.archInfo.countLimit,
            defaultOrderBy: this.archInfo.defaultOrder,
            groupsLimit: this.archInfo.groupsLimit,
            multiEdit: !this.props.readonly && this.archInfo.multiEdit,
            activeIdsLimit: session.active_ids_limit,
            hooks: {
                ...this._uiHooks,
                onRecordSaved: this.onRecordSaved.bind(this),
                onWillSaveRecord: this.onWillSaveRecord.bind(this),
                onWillSaveMulti: this.onWillSaveMulti.bind(this),
                onAskMultiSaveConfirmation: this.onAskMultiSaveConfirmation.bind(this),
                onWillSetInvalidField: this.onWillSetInvalidField.bind(this),
            },
        };
    }

    get className() {
        return this.props.className;
    }

    // -------------------------------------------------------------------------
    // Methods
    // -------------------------------------------------------------------------

    /**
     * Return the list of exportable field definitions for the current columns.
     *
     * Filters out optional-hidden, column-invisible, non-exportable, and
     * properties-type columns, then deduplicates by field identity.
     *
     * @returns {any[]} unique exportable field objects
     */
    getExportableFields() {
        return unique(
            this.props.archInfo.columns
                .filter((col) => col.type === "field")
                .filter((col) => !col.optional || this.optionalActiveFields[col.name])
                .filter(
                    (col) =>
                        !evaluateBooleanExpr(col.column_invisible, this.props.context),
                )
                .map((col) => this.props.fields[col.name])
                .filter((field) => field.exportable !== false)
                .filter((field) => field.type !== "properties"),
        );
    }

    /**
     * Hook called before navigating away. Leaves edit mode gracefully.
     *
     * @param {Event} ev
     * @returns {Promise<any>}
     */
    async beforeLeave(ev) {
        return this.model.root.leaveEditMode();
    }

    /**
     * Hook called before the page unloads. Attempts an urgent save of the
     * edited record and blocks unload if validation fails.
     *
     * @param {BeforeUnloadEvent} ev
     */
    async beforeUnload(ev) {
        if (this.editedRecord) {
            const isValid = await this.editedRecord.urgentSave();
            if (!isValid) {
                ev.preventDefault();
                ev.returnValue = "Unsaved changes";
            }
        }
    }

    /**
     * onRecordSaved is a callBack that will be executed after the save
     * if it was done. It will therefore not be executed if the record
     * is invalid or if a server error is thrown.
     * @param {any} record
     */
    async onRecordSaved(record) {}

    /**
     * onWillSaveRecord is a callBack that will be executed before the
     * record save if the record is valid.
     * If it returns false, it will prevent the save.
     * @param {any} record
     */
    async onWillSaveRecord(record) {}

    /**
     * Create a new record, either inline (editable list) or via form view.
     *
     * In editable non-grouped lists, adds a new row at top or bottom. In
     * grouped or non-editable lists, delegates to the parent's createRecord.
     *
     * @param {{ group?: any }} [options]
     */
    async createRecord({ group } = /** @type {any} */ ({})) {
        if (!this.model.isReady && !this.model.config.groupBy.length && this.editable) {
            // If the view isn't grouped and the list is editable, a new record row will be added,
            // in edition. In this situation, we must wait for the model to be ready.
            await this.model.whenReady;
        }
        const list = group?.list || this.model.root;
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

    /**
     * Open a record, either via a custom action or by navigating to the form view.
     *
     * Saves dirty records first. Respects `archInfo.openAction` for custom
     * action-on-click, otherwise delegates to `props.selectRecord`.
     *
     * @param {any} record - the record to open
     * @param {{ force?: boolean, newWindow?: boolean }} [options]
     */
    async openRecord(
        record,
        { force, newWindow } = /** @type {any} */ ({ force: false }),
    ) {
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
                },
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

    /** Handle click on the "New" / "Create" button. */
    async onClickCreate() {
        return executeButtonCallback(this.rootRef.el, () => this.createRecord());
    }

    /** Handle click on the "Discard" button — leaves edit mode without saving. */
    async onClickDiscard() {
        return executeButtonCallback(this.rootRef.el, () =>
            this.model.root.leaveEditMode({ discard: true }),
        );
    }

    /** Handle click on the "Save" button — saves the edited record and leaves edit mode. */
    async onClickSave() {
        return executeButtonCallback(this.rootRef.el, async () => {
            const saved = await this.editedRecord.save();
            if (saved) {
                await this.model.root.leaveEditMode();
            }
        });
    }

    /**
     * Track mousedown on "Discard" to defer multi-save until mouseup.
     *
     * Prevents saving when the user starts clicking on "Discard" but moves
     * the cursor away before releasing — the deferred action fires on mouseup
     * only if the target differs from the original mousedown target.
     *
     * @param {MouseEvent} mouseDownEvent
     */
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
            { capture: true, once: true },
        );
    }

    /** Reset the renderer scroll position to the top after a pager navigation. */
    onPageChangeScroll() {
        if (this.rootRef?.el) {
            if (this.env.isSmall) {
                this.rootRef.el.scrollTop = 0;
            } else {
                this.rootRef.el.querySelector(".o_content .o_list_renderer").scrollTop =
                    0;
            }
        }
    }

    /**
     * Evaluate a view modifier expression against the root list's eval context.
     *
     * @param {string} modifier - boolean expression string
     * @returns {boolean}
     */
    evalViewModifier(modifier) {
        return evaluateBooleanExpr(modifier, this.model.root.evalContext);
    }

    /** Deselect all currently selected records. */
    discardSelection() {
        this.model.root.records.forEach((record) => {
            record.toggleSelection(false);
        });
    }

    /**
     * Save the edited record before executing a non-cancel action button.
     *
     * @param {{ special?: string }} clickParams
     * @returns {Promise<boolean | undefined>} false if save failed
     */
    async beforeExecuteActionButton(clickParams) {
        if (clickParams.special !== "cancel" && this.editedRecord) {
            return this.editedRecord.save();
        }
    }

    /**
     * Show a confirmation dialog before applying multi-edit changes.
     *
     * Opens {@link ListConfirmationDialog} when more than one record is
     * selected and at least one is valid for the update. Returns a promise
     * that resolves to `true` (confirmed) or `false` (cancelled).
     *
     * @param {Record<string, any>} changes - field name to new value mapping
     * @param {any[]} validSelectedRecords - records eligible for the update
     * @returns {Promise<boolean> | boolean}
     */
    onAskMultiSaveConfirmation(changes, validSelectedRecords) {
        if (this.model.root.selection.length > 1 && validSelectedRecords.length > 0) {
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
                    document.activeElement.closest(".o_data_cell")
                );
                this.dialogService.add(ListConfirmationDialog, dialogProps, {
                    onClose: () => {
                        if (focusedCellBeforeDialog) {
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
     * Guard hook before multi-save. Defers save if "Discard" mousedown is active.
     *
     * @param {any} editedRecord
     * @param {Record<string, any>} changes
     * @returns {boolean} false to block the save
     */
    onWillSaveMulti(editedRecord, changes) {
        if (this.hasMousedownDiscard) {
            this.nextActionAfterMouseup = () =>
                this.model.root.multiSave(editedRecord, changes);
            return false;
        }
        return true;
    }

    /**
     * Guard hook before marking a field invalid. Defers if "Discard" mousedown is active.
     *
     * @param {any} record
     * @param {string} fieldName
     * @returns {boolean} false to block the invalid notification
     */
    onWillSetInvalidField(record, fieldName) {
        if (this.hasMousedownDiscard) {
            this.nextActionAfterMouseup = () => record.setInvalidField(fieldName);
            return false;
        }
        return true;
    }
}
