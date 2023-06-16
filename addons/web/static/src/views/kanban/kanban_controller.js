/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { Layout } from "@web/search/layout";
import { usePager } from "@web/search/pager_hook";
import { useModel } from "@web/views/model";
import { standardViewProps } from "@web/views/standard_view_props";
import { MultiRecordViewButton } from "@web/views/view_button/multi_record_view_button";
import { useViewButtons } from "@web/views/view_button/view_button_hook";
import { useSetupView } from "@web/views/view_hook";
import { KanbanRenderer } from "./kanban_renderer";
import { useProgressBar } from "./progress_bar_hook";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { useSearchBarToggler } from "@web/search/search_bar/search_bar_toggler";
import { CogMenu } from "@web/search/cog_menu/cog_menu";

import { Component, reactive, useRef } from "@odoo/owl";
import { addDependencies } from "../utils";

const QUICK_CREATE_FIELD_TYPES = ["char", "boolean", "many2one", "selection", "many2many"];

// -----------------------------------------------------------------------------

export class KanbanController extends Component {
    setup() {
        this.actionService = useService("action");
        const { Model, archInfo } = this.props;
        this.model = useModel(Model, this.modelParams, this.modelOptions);
        if (archInfo.progressAttributes) {
            const { activeBars } = this.props.state || {};
            this.progressBarState = useProgressBar(
                archInfo.progressAttributes,
                this.model,
                this.progressBarAggregateFields,
                activeBars
            );
        }
        this.headerButtons = archInfo.headerButtons;

        const self = this;
        this.quickCreateState = reactive({
            get groupId() {
                return this._groupId || false;
            },
            set groupId(groupId) {
                if (self.model.useSampleModel) {
                    self.model.useSampleModel = false;
                    self.model.root.groups.forEach((g) => g.empty());
                    self.render();
                }
                this._groupId = groupId;
            },
            view: archInfo.quickCreateView,
        });

        this.rootRef = useRef("root");
        useViewButtons(this.model, this.rootRef, {
            beforeExecuteAction: this.beforeExecuteActionButton.bind(this),
            afterExecuteAction: this.afterExecuteActionButton.bind(this),
        });
        useSetupView({
            rootRef: this.rootRef,
            getGlobalState: () => {
                return {
                    resIds: this.model.root.records.map((rec) => rec.resId), // WOWL: ask LPE why?
                };
            },
            getLocalState: () => {
                return {
                    activeBars: this.progressBarState?.activeBars,
                    rootState: this.model.root.exportState(),
                };
            },
        });
        usePager(() => {
            const root = this.model.root;
            const { count, hasLimitedCount, isGrouped, limit, offset } = root;
            if (!isGrouped) {
                return {
                    offset: offset,
                    limit: limit,
                    total: count,
                    onUpdate: async ({ offset, limit }) => {
                        this.model.root.offset = offset;
                        this.model.root.limit = limit;
                        await this.model.root.load();
                        await this.onUpdatedPager();
                        this.render(true); // FIXME WOWL reactivity
                    },
                    updateTotal: hasLimitedCount ? () => root.fetchCount() : undefined,
                };
            }
        });
        this.searchBarToggler = useSearchBarToggler();
    }

    get modelParams() {
        const { resModel, fields, archInfo, limit, defaultGroupBy, state } = this.props;
        const { rootState } = state || {};

        const activeFields = archInfo.activeFields;
        addDependencies(this.progressBarAggregateFields, activeFields, fields);

        return {
            activeFields,
            fields: { ...fields },
            resModel,
            handleField: archInfo.handleField,
            limit: archInfo.limit || limit,
            countLimit: archInfo.countLimit,
            defaultGroupBy,
            defaultOrder: archInfo.defaultOrder,
            viewMode: "kanban",
            openGroupsByDefault: true,
            onRecordSaved: this.onRecordSaved.bind(this),
            rootState,
        };
    }

    get modelOptions(){
        return {};
    }

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

    async openRecord(record, mode) {
        const activeIds = this.model.root.records.map((datapoint) => datapoint.resId);
        this.props.selectRecord(record.resId, { activeIds, mode });
    }

    async createRecord() {
        const { onCreate } = this.props.archInfo;
        const { root } = this.model;
        if (this.canQuickCreate && onCreate === "quick_create") {
            const firstGroup = root.groups[0];
            if (firstGroup.isFolded) {
                await firstGroup.toggle();
            }
            this.quickCreateState.groupId = firstGroup.id;
        } else if (onCreate && onCreate !== "quick_create") {
            const options = {
                additionalContext: root.context,
                onClose: async () => {
                    await root.load();
                    this.model.useSampleModel = false;
                    this.render(true); // FIXME WOWL reactivity
                },
            };
            await this.actionService.doAction(onCreate, options);
        } else {
            await this.props.createRecord();
        }
    }

    get canCreate() {
        const { create, createGroup } = this.props.archInfo.activeActions;
        const list = this.model.root;
        if (!create) {
            return false;
        }
        return list.isGrouped ? list.groups.length > 0 || !createGroup : true;
    }

    get canQuickCreate() {
        const { activeActions } = this.props.archInfo;
        if (!activeActions.quickCreate) {
            return false;
        }

        const list = this.model.root;
        if (list.groups && !list.groups.length) {
            return false;
        }

        return this.isQuickCreateField(list.groupByField);
    }

    onRecordSaved(record) {
        if (this.model.root.isGrouped) {
            const group = this.model.root.groups.find((l) =>
                l.records.find((r) => r.id === record.id)
            );
            this.progressBarState?.updateCounts(group);
        }
    }

    async beforeExecuteActionButton(clickParams) {}

    async afterExecuteActionButton(clickParams) {}

    async onUpdatedPager() {}

    scrollTop() {
        this.rootRef.el.querySelector(".o_content").scrollTo({ top: 0 });
    }

    isQuickCreateField(field) {
        return field && QUICK_CREATE_FIELD_TYPES.includes(field.type);
    }
}

KanbanController.template = `web.KanbanView`;
KanbanController.components = { Layout, KanbanRenderer, MultiRecordViewButton, SearchBar, CogMenu };
KanbanController.props = {
    ...standardViewProps,
    defaultGroupBy: { validate: (dgb) => !dgb || typeof dgb === "string", optional: true },
    editable: { type: Boolean, optional: true },
    forceGlobalClick: { type: Boolean, optional: true },
    onSelectionChanged: { type: Function, optional: true },
    showButtons: { type: Boolean, optional: true },
    Compiler: { type: Function, optional: true }, // optional in stable for backward compatibility
    Model: Function,
    Renderer: Function,
    buttonTemplate: String,
    archInfo: Object,
};

KanbanController.defaultProps = {
    createRecord: () => {},
    forceGlobalClick: false,
    selectRecord: () => {},
    showButtons: true,
};
