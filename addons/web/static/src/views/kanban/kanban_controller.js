/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { Layout } from "@web/search/layout";
import { usePager } from "@web/search/pager_hook";
import { useModel } from "@web/views/model";
import { standardViewProps } from "@web/views/standard_view_props";
import { useSetupView } from "@web/views/view_hook";
import { useViewButtons } from "@web/views/view_button/view_button_hook";
import { KanbanRenderer } from "./kanban_renderer";

import { Component, useRef } from "@odoo/owl";

// -----------------------------------------------------------------------------

export class KanbanController extends Component {
    setup() {
        this.actionService = useService("action");
        const { Model, resModel, fields, archInfo, limit, defaultGroupBy, state } = this.props;
        const { rootState } = state || {};
        this.model = useModel(Model, {
            activeFields: archInfo.activeFields,
            progressAttributes: archInfo.progressAttributes,
            fields,
            resModel,
            handleField: archInfo.handleField,
            limit: archInfo.limit || limit,
            countLimit: archInfo.countLimit,
            onCreate: archInfo.onCreate,
            quickCreateView: archInfo.quickCreateView,
            defaultGroupBy,
            defaultOrder: archInfo.defaultOrder,
            viewMode: "kanban",
            openGroupsByDefault: true,
            tooltipInfo: archInfo.tooltipInfo,
            rootState,
        });

        const rootRef = useRef("root");
        useViewButtons(this.model, rootRef, {
            beforeExecuteAction: this.beforeExecuteActionButton.bind(this),
            afterExecuteAction: this.afterExecuteActionButton.bind(this),
        });
        useSetupView({
            rootRef,
            getGlobalState: () => {
                return {
                    resIds: this.model.root.records.map((rec) => rec.resId), // WOWL: ask LPE why?
                };
            },
            getLocalState: () => {
                return {
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

    async createRecord(group) {
        const { activeActions, onCreate } = this.props.archInfo;
        const { root } = this.model;
        if (activeActions.quickCreate && onCreate === "quick_create" && root.canQuickCreate()) {
            await root.quickCreate(group);
        } else if (onCreate && onCreate !== "quick_create") {
            const options = {
                additionalContext: root.context,
                onClose: async () => {
                    await this.model.root.load();
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
        if (list.isGrouped) {
            if (list.groupByField.type !== "many2one") {
                return true;
            }
            return list.groups.length || !createGroup;
        }
        return true;
    }

    async beforeExecuteActionButton(clickParams) {}

    async afterExecuteActionButton(clickParams) {}

    async onUpdatedPager() {}
}

KanbanController.template = `web.KanbanView`;
KanbanController.components = { Layout, KanbanRenderer };
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
