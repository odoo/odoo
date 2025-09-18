// @ts-check

/** @module @web/views/kanban/kanban_controller - Controller for the kanban view with grouping, quick-create, and progress bar support */

import { reactive, useEffect, useState } from "@odoo/owl";
import { DropdownItem } from "@web/components/dropdown/dropdown_item";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { useModelWithSampleData } from "@web/model/model";
import {
    addFieldDependencies,
    extractFieldsFromArchInfo,
} from "@web/model/relational_model/utils";
import { useSetupAction } from "@web/search/action_hook";
import { ActionMenus } from "@web/search/action_menus/action_menus";
import { Layout } from "@web/search/layout";
import { usePager } from "@web/search/pager_hook";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { session } from "@web/session";
import { MultiRecordController } from "@web/views/multi_record_controller";
import { standardViewProps } from "@web/views/standard_view_props";
import { MultiRecordViewButton } from "@web/views/view_button/multi_record_view_button";
import { SelectionBox } from "@web/views/view_components/selection_box";

import { KanbanCogMenu } from "./kanban_cog_menu";
import { KanbanRenderer } from "./kanban_renderer";
import { useProgressBar } from "./progress_bar_hook";

const QUICK_CREATE_FIELD_TYPES = [
    "char",
    "boolean",
    "many2one",
    "selection",
    "many2many",
];

// -----------------------------------------------------------------------------

/**
 * Main controller for the kanban view, extending MultiRecordController.
 *
 * Manages the kanban-specific model (with sample data support), progress bar
 * state, quick-create workflow, column scroll restoration, and record CRUD
 * actions (open, create, delete). Coordinates between the KanbanRenderer,
 * RelationalModel, and pager.
 */
export class KanbanController extends MultiRecordController {
    static template = `web.KanbanView`;
    static components = {
        ActionMenus,
        DropdownItem,
        Layout,
        KanbanRenderer,
        MultiRecordViewButton,
        SearchBar,
        CogMenu: KanbanCogMenu,
        SelectionBox,
    };
    static props = {
        ...standardViewProps,
        editable: { type: Boolean, optional: true },
        forceGlobalClick: { type: Boolean, optional: true },
        onSelectionChanged: { type: Function, optional: true },
        readonly: { type: Boolean, optional: true },
        showButtons: { type: Boolean, optional: true },
        Compiler: Function,
        Model: Function,
        Renderer: Function,
        buttonTemplate: String,
        archInfo: Object,
    };

    static defaultProps = {
        createRecord: () => {},
        forceGlobalClick: false,
        selectRecord: () => {},
        showButtons: true,
    };

    setup() {
        super.setup();

        // --- Kanban-specific model with sample data override ---
        const { Model } = this.props;

        class KanbanSampleModel extends Model {
            hasData() {
                if (this.root.groups && !this.root.groups.length) {
                    // While we don't have any data, we want to display the column quick create and
                    // example background. Return true so that we don't get sample data instead
                    return true;
                }
                return super.hasData();
            }

            removeSampleDataInGroups() {
                if (this.useSampleModel) {
                    for (const group of this.root.groups) {
                        const list = group.list;
                        group.count = 0;
                        list.count = 0;
                        if (list._records !== undefined) {
                            list._records = [];
                        } else {
                            list.groups = [];
                        }
                    }
                }
            }
        }

        this.model = useState(
            useModelWithSampleData(
                /** @type {any} */ (KanbanSampleModel),
                this.modelParams,
                /** @type {any} */ (this.modelOptions),
            ),
        );

        // --- Progress bar ---
        if (this.archInfo.progressAttributes) {
            const { activeBars } = this.props.state || {};
            this.progressBarState = useProgressBar(
                this.archInfo.progressAttributes,
                this.model,
                this.progressBarAggregateFields,
                activeBars,
            );
        }
        this.headerButtons = this.archInfo.headerButtons;

        // --- Quick create ---
        const self = this;
        this.quickCreateState = reactive(
            /** @type {any} */ ({
                get groupId() {
                    return this._groupId || false;
                },
                set groupId(groupId) {
                    if (self.model.useSampleModel) {
                        self.model.removeSampleDataInGroups();
                        self.model.useSampleModel = false;
                    }
                    this._groupId = groupId;
                },
                view: this.archInfo.quickCreateView,
            }),
        );

        // --- Common post-model behavior ---
        this.initMultiRecordBehavior();

        // --- Kanban-specific hooks ---
        const { setScrollFromState } = useSetupAction({
            rootRef: this.rootRef,
            beforeUnload: this.beforeUnload.bind(this),
            beforeLeave: this.beforeLeave.bind(this),
            getLocalState: () => {
                const state = {
                    activeBars: this.progressBarState?.activeBars,
                    modelState: this.model.exportState(),
                };
                if (this.env.isSmall && this.model.root.isGrouped) {
                    const columnScrollTops = [];
                    const sel = ".o_kanban_group:not(.o_column_folded)";
                    const columnEls = this.rootRef.el.querySelectorAll(sel);
                    const groups = this.model.root.groups;
                    for (const columnEl of columnEls) {
                        const scrollTop = columnEl.scrollTop;
                        if (scrollTop > 0) {
                            const group = groups.find(
                                (g) => g.id === columnEl.dataset.id,
                            );
                            columnScrollTops.push([
                                group.serverValue,
                                columnEl.scrollTop,
                            ]);
                        }
                    }
                    state.scrollPositions = {
                        scrollLeft:
                            this.rootRef.el.querySelector(".o_renderer")?.scrollLeft ||
                            0,
                        columnScrollTops,
                    };
                }
                return state;
            },
        });
        useEffect(
            (isReady) => {
                if (isReady) {
                    if (this.env.isSmall && this.model.root.isGrouped) {
                        const { scrollPositions } = this.props.state || {};
                        if (scrollPositions) {
                            const { scrollLeft, columnScrollTops } = scrollPositions;
                            this.rootRef.el.querySelector(".o_renderer").scrollLeft =
                                scrollLeft;
                            const groups = this.model.root.groups;
                            for (const [serverValue, scrollTop] of columnScrollTops) {
                                const group = groups.find(
                                    (g) => g.serverValue === serverValue,
                                );
                                if (group) {
                                    const sel = `.o_kanban_group[data-id=${group.id}]`;
                                    this.rootRef.el.querySelector(sel).scrollTop =
                                        scrollTop;
                                }
                            }
                        }
                    } else {
                        setScrollFromState();
                    }
                }
            },
            () => [this.model.isReady],
        );
        usePager(() => {
            const root = this.model.root;
            const { count, hasLimitedCount, isGrouped, limit, offset } = root;
            if (!isGrouped && !this.model.useSampleModel) {
                return {
                    offset: offset,
                    limit: limit,
                    total: count,
                    onUpdate: async ({ offset, limit }, hasNavigated) => {
                        await this.model.root.load({ offset, limit });
                        await this.onUpdatedPager();
                        if (hasNavigated) {
                            this.onPageChangeScroll();
                        }
                    },
                    updateTotal: hasLimitedCount ? () => root.fetchCount() : undefined,
                };
            }
        });
    }

    // -------------------------------------------------------------------------
    // Getters
    // -------------------------------------------------------------------------

    /** @returns {Object} Configuration object passed to the RelationalModel constructor. */
    get modelParams() {
        const { resModel, limit } = this.props;
        const { activeFields, fields } = extractFieldsFromArchInfo(
            this.archInfo,
            this.props.fields,
        );

        const cardColorField = this.archInfo.cardColorField;
        if (cardColorField) {
            addFieldDependencies(activeFields, fields, [
                { name: cardColorField, type: "integer" },
            ]);
        }

        addFieldDependencies(activeFields, fields, this.progressBarAggregateFields);
        const modelConfig = this.props.state?.modelState?.config || {
            resModel,
            activeFields,
            fields,
            fieldsToAggregate: this.progressBarAggregateFields.map(
                (field) => field.name,
            ),
            openGroupsByDefault: true,
        };

        return {
            config: modelConfig,
            state: this.props.state?.modelState,
            limit: this.archInfo.limit || limit || 40,
            groupsLimit: Number.MAX_SAFE_INTEGER, // no limit
            countLimit: this.archInfo.countLimit,
            defaultOrderBy: this.archInfo.defaultOrder,
            maxGroupByDepth: 1,
            activeIdsLimit: session.active_ids_limit,
            hooks: {
                ...this._uiHooks,
                onRecordSaved: this.onRecordSaved.bind(this),
            },
        };
    }

    /** @returns {Object[]} Fields to aggregate in progress bar computations. */
    get progressBarAggregateFields() {
        const res = [];
        const { progressAttributes } = this.props.archInfo;
        if (progressAttributes && progressAttributes.sumField) {
            res.push(progressAttributes.sumField);
        }
        return res;
    }

    get className() {
        if (this.env.isSmall && this.model.root.isGrouped) {
            const classList = (this.props.className || "").split(" ");
            classList.push("o_action_delegate_scroll");
            return classList.join(" ");
        }
        return this.props.className;
    }

    /** @returns {boolean} Whether the user can create new records. */
    get canCreate() {
        return this.props.archInfo.activeActions.create;
    }

    /** @returns {boolean} Whether the "New" button should be disabled (e.g. empty many2one grouping). */
    get isNewButtonDisabled() {
        const { createGroup } = this.props.archInfo.activeActions;
        const list = this.model.root;
        return (
            this.model.isReady &&
            list.isGrouped &&
            list.groupByField.type === "many2one" &&
            list.groups.length === 0 &&
            createGroup
        );
    }

    /** @returns {boolean} Whether quick-create is available for the current group-by field. */
    get canQuickCreate() {
        const { activeActions } = this.props.archInfo;
        if (!activeActions.quickCreate) {
            return false;
        }
        if (!this.model.isReady) {
            return false;
        }

        const list = this.model.root;
        if (list.groups && !list.groups.length) {
            return false;
        }

        return this.isQuickCreateField(list.groupByField);
    }

    // -------------------------------------------------------------------------
    // Methods
    // -------------------------------------------------------------------------

    /** @returns {Object[]} Field definitions eligible for data export (excludes properties). */
    getExportableFields() {
        return Object.keys(this.model.root.config.activeFields)
            .map((e) => this.props.fields[e])
            .filter((field) => field.type !== "properties");
    }

    async beforeUnload() {}

    async beforeLeave() {
        // wait for potential pending write operations (e.g. records being moved)
        return this.model.mutex.getUnlockedDef();
    }

    /**
     * Evaluate a view modifier expression in the current context.
     * @param {string} modifier - Boolean expression string.
     * @returns {boolean}
     */
    evalViewModifier(modifier) {
        return evaluateBooleanExpr(modifier, { context: this.props.context });
    }

    /**
     * Delete a single record with a confirmation dialog.
     * @param {Object} record - The record datapoint to delete.
     */
    deleteRecord(record) {
        this.deleteRecordsWithConfirmation(this.deleteConfirmationDialogProps, [
            record,
        ]);
    }

    async openRecord(record, /** @type {any} */ { newWindow } = {}) {
        const activeIds = this.model.root.records.map((datapoint) => datapoint.resId);
        this.props.selectRecord(record.resId, { activeIds, newWindow });
    }

    /**
     * Create a new record via quick-create, custom action, or default flow.
     * Dispatches based on the `on_create` arch attribute.
     */
    async createRecord() {
        const { onCreate } = this.props.archInfo;
        const { root } = this.model;
        if (this.canQuickCreate && onCreate === "quick_create") {
            const firstGroup =
                root.groups.find((group) => !group.isFolded) || root.groups[0];
            if (firstGroup.isFolded) {
                await firstGroup.toggle();
            }
            this.quickCreateState.groupId = firstGroup.id;
        } else if (onCreate && onCreate !== "quick_create") {
            const options = {
                additionalContext: root.context,
                onClose: async (/** @type {any} */ { noReload } = {}) => {
                    if (!noReload) {
                        await root.load();
                        this.model.useSampleModel = false;
                        this.render(true); // FIXME WOWL reactivity
                    }
                },
            };
            await this.actionService.doAction(onCreate, options);
        } else {
            await this.props.createRecord();
        }
    }

    /**
     * Update progress bar counts after a record is saved in a grouped view.
     * @param {Object} record - The saved record datapoint.
     */
    onRecordSaved(record) {
        if (this.model.root.isGrouped) {
            const group = this.model.root.groups.find((l) =>
                l.records.find((r) => r.id === record.id),
            );
            this.progressBarState?.updateCounts(group);
        }
    }

    async onUpdatedPager() {}

    /** Scroll the content area to the top. */
    scrollTop() {
        this.rootRef.el.querySelector(".o_content").scrollTo({ top: 0 });
    }

    /**
     * Check whether a field type supports quick-create grouping.
     * @param {Object | null} field - Field definition with a `type` property.
     * @returns {boolean}
     */
    isQuickCreateField(field) {
        return field && QUICK_CREATE_FIELD_TYPES.includes(field.type);
    }
}
