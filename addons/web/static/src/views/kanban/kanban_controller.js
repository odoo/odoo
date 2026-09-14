// @ts-check
/** @odoo-module native */

import { reactive, useEffect, useState } from "@odoo/owl";
import { DropdownItem } from "@web/components/dropdown/dropdown_item";
import { useSetupAction } from "@web/core/action_hook";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useModelWithSampleData } from "@web/model/model";
import {
    addFieldDependencies,
    extractFieldsFromArchInfo,
} from "@web/model/relational_model";
import { ActionMenus } from "@web/search/action_menus/action_menus";
import { MultiRecordCogMenu } from "@web/views/multi_record_cog_menu";
import { MultiRecordController } from "@web/views/multi_record_controller";
import { standardViewProps } from "@web/views/standard_view_props";
import { MultiRecordViewButton } from "@web/views/view_button/multi_record_view_button";
import { SelectionBox } from "@web/views/view_components/selection_box";
import { ViewLayout } from "@web/views/view_components/view_layout";
import { exportableFields, getMultiRecordModelParams } from "@web/views/view_utils";

import { KanbanRenderer } from "./kanban_renderer.js";
import { useProgressBar } from "./progress_bar_hook.js";

/** @type {WeakMap<Function, Function>} */
const sampleModelByModel = new WeakMap();

/**
 * @param {any} Model
 * @returns {any}
 */
function kanbanSampleModel(Model) {
    let KanbanSampleModel = sampleModelByModel.get(Model);
    if (!KanbanSampleModel) {
        KanbanSampleModel = class KanbanSampleModel extends Model {
            hasData() {
                if (this.root.groups && !this.root.groups.length) {
                    return true;
                }
                return super.hasData();
            }

            removeSampleDataInGroups() {
                if (this.useSampleModel) {
                    for (const group of this.root.groups) {
                        group.count = 0;
                        group.list.clearSampleData();
                    }
                }
            }
        };
        sampleModelByModel.set(Model, KanbanSampleModel);
    }
    return KanbanSampleModel;
}

const QUICK_CREATE_FIELD_TYPES = [
    "char",
    "boolean",
    "many2one",
    "selection",
    "many2many",
];

const log = makeLogger("web.view.kanban");

export class KanbanController extends MultiRecordController {
    static template = `web.KanbanView`;
    static components = {
        ActionMenus,
        DropdownItem,
        ViewLayout,
        KanbanRenderer,
        MultiRecordViewButton,
        CogMenu: MultiRecordCogMenu,
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

    /** @override */
    setupModel() {
        this.model = useState(
            useModelWithSampleData(
                /** @type {any} */ (kanbanSampleModel(this.props.Model)),
                this.modelParams,
                /** @type {any} */ (this.modelOptions),
            ),
        );

        if (this.archInfo.progressAttributes) {
            const { activeBars } = this.props.state || {};
            this.progressBarState = useProgressBar(
                this.archInfo.progressAttributes,
                this.model,
                this.progressBarAggregateFields,
                activeBars,
            );
        }
        const self = this;
        this.quickCreateState = reactive(
            /** @type {any} */ ({
                get groupId() {
                    if (!this._groupId) {
                        return false;
                    }
                    const groups = self.model.root.groups || [];
                    if (groups.some((group) => group.id === this._groupId)) {
                        return this._groupId;
                    }
                    const groupBy = self.model.root.groupBy;
                    const regrouped = groups.find(
                        (group) =>
                            JSON.stringify([groupBy, group.serverValue]) ===
                            this._groupKey,
                    );
                    return regrouped ? regrouped.id : false;
                },
                // eslint-disable-next-line no-restricted-syntax -- must clear sample data synchronously with this mutation; see STATE_MANAGEMENT.md "Pattern 4"
                set groupId(groupId) {
                    if (self.model.useSampleModel) {
                        self.model.removeSampleDataInGroups();
                        self.model.useSampleModel = false;
                    }
                    this._groupId = groupId;
                    const group = (self.model.root.groups || []).find(
                        (candidate) => candidate.id === groupId,
                    );
                    this._groupKey = group
                        ? JSON.stringify([self.model.root.groupBy, group.serverValue])
                        : undefined;
                },
                view: this.archInfo.quickCreateView,
            }),
        );
    }

    /** @override */
    setupInteractions() {
        const { setScrollFromState } = useSetupAction({
            rootRef: this.rootRef,
            beforeUnload: this.beforeUnload.bind(this),
            beforeLeave: this.beforeLeave.bind(this),
            getLocalState: () => this.getLocalState(),
        });
        useEffect(
            (isReady) => {
                if (!isReady) {
                    return;
                }
                if (this.env.isSmall && this.model.root.isGrouped) {
                    this.restoreColumnScrollPositions();
                } else {
                    setScrollFromState();
                }
            },
            () => [this.model.isReady],
        );
        this.setupPager();
    }

    /** @param {any} root */
    pagerEnabled(root) {
        return !root.isGrouped;
    }

    /** @returns {Record<string, any>} */
    getLocalState() {
        const state = {
            activeBars: this.progressBarState?.activeBars,
            modelState: this.model.exportState(),
        };
        if (this.env.isSmall && this.model.root.isGrouped) {
            state.scrollPositions = this.getColumnScrollPositions();
        }
        return state;
    }

    /** @returns {{ scrollLeft: number, columnScrollTops: [any, number][] }} */
    getColumnScrollPositions() {
        /** @type {[any, number][]} */
        const columnScrollTops = [];
        const sel = ".o_kanban_group:not(.o_column_folded)";
        const columnEls = /** @type {HTMLElement} */ (this.rootRef.el).querySelectorAll(
            sel,
        );
        const groups = this.model.root.groups;
        for (const columnEl of columnEls) {
            const scrollTop = columnEl.scrollTop;
            if (scrollTop > 0) {
                const group = groups.find((g) => g.id === columnEl.dataset.id);
                if (group) {
                    columnScrollTops.push([group.serverValue, columnEl.scrollTop]);
                }
            }
        }
        return {
            scrollLeft: this.rootRef.el?.querySelector(".o_renderer")?.scrollLeft || 0,
            columnScrollTops,
        };
    }

    restoreColumnScrollPositions() {
        const { scrollPositions } = this.props.state || {};
        if (!scrollPositions) {
            return;
        }
        const { scrollLeft, columnScrollTops } = scrollPositions;
        const renderer = this.rootRef.el?.querySelector(".o_renderer");
        if (renderer) {
            renderer.scrollLeft = scrollLeft;
        }
        const groups = this.model.root.groups;
        for (const [serverValue, scrollTop] of columnScrollTops) {
            const group = groups.find((g) => g.serverValue === serverValue);
            if (group) {
                const sel = `.o_kanban_group[data-id="${group.id}"]`;
                const el = this.rootRef.el?.querySelector(sel);
                if (el) {
                    el.scrollTop = scrollTop;
                }
            }
        }
    }

    /** @returns {Object} */
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

        return getMultiRecordModelParams({
            archInfo: this.archInfo,
            props: this.props,
            uiHooks: this._uiHooks,
            config: {
                resModel,
                activeFields,
                fields,
                fieldsToAggregate: this.progressBarAggregateFields.map(
                    (field) => field.name,
                ),
                openGroupsByDefault: true,
            },
            hooks: {
                lifecycle: {
                    onRecordSaved: this.onRecordSaved.bind(this),
                },
            },
            extras: {
                limit: this.archInfo.limit || limit || 40,
                groupsLimit: Number.MAX_SAFE_INTEGER,
                maxGroupByDepth: 1,
            },
        });
    }

    /** @returns {Object[]} */
    get progressBarAggregateFields() {
        const res = [];
        const { progressAttributes } = this.props.archInfo;
        if (progressAttributes?.sumField) {
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

    get chassisProps() {
        const selection = this.hasSelectedRecords
            ? "o_kanban_selection_active"
            : "o_kanban_selection_available";
        return { ...super.chassisProps, className: `${this.className} ${selection}` };
    }

    /** @returns {boolean} */
    get canCreate() {
        return this.props.archInfo.activeActions.create;
    }

    /** @returns {boolean} */
    get isNewButtonDisabled() {
        const { createGroup } = this.props.archInfo.activeActions;
        const list = this.model.root;
        return (
            this.model.isReady &&
            list.isGrouped &&
            list.groupByField.type === "many2one" &&
            !list.groups.length &&
            createGroup
        );
    }

    /** @returns {boolean} */
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

    /** @returns {Object[]} */
    getExportableFields() {
        const { activeFields, fields } = this.model.root;
        return exportableFields(fields, activeFields);
    }

    async beforeUnload() {}

    async beforeLeave() {
        return this.model.mutex.getUnlockedDef();
    }

    /** @param {Object} record */
    deleteRecord(record) {
        this.deleteRecordsWithConfirmation(this.deleteConfirmationDialogProps, [
            record,
        ]);
    }

    async openRecord(record, /** @type {any} */ { newWindow } = {}) {
        log.logic("openRecord", () => ({
            resModel: record.resModel,
            resId: record.resId,
            newWindow,
        }));
        const activeIds = this.model.root.records.map((datapoint) => datapoint.resId);
        this.props.selectRecord(record.resId, { activeIds, newWindow });
    }

    async createRecord() {
        const { onCreate } = this.props.archInfo;
        const { root } = this.model;
        log.logic("createRecord", () => ({
            onCreate,
            quickCreate: this.canQuickCreate,
            grouped: root.isGrouped,
        }));
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
                        this.render();
                    }
                },
            };
            await this.actionService.doAction(onCreate, options);
        } else {
            await this.props.createRecord();
        }
    }

    /** @param {Object} record */
    onRecordSaved(record) {
        log.lifecycle("onRecordSaved", () => ({
            resModel: record.resModel,
            resId: record.resId,
            grouped: this.model.root.isGrouped,
        }));
        if (this.model.root.isGrouped) {
            const group = this.model.root.groups.find((l) =>
                l.records.find((r) => r.id === record.id),
            );
            this.progressBarState?.updateCounts(group, record);
        }
    }

    scrollTop() {
        this.onPageChangeScroll();
    }

    /**
     * @param {Object | null} field
     * @returns {boolean}
     */
    isQuickCreateField(field) {
        return field && QUICK_CREATE_FIELD_TYPES.includes(field.type);
    }
}
