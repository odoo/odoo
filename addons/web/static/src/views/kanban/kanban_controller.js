/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { Layout } from "@web/search/layout";
import { usePager } from "@web/search/pager_hook";
import { useModel } from "@web/views/model";
import { standardViewProps } from "@web/views/standard_view_props";
import { useSetupView } from "@web/views/view_hook";
import { useViewButtons } from "@web/views/view_button/view_button_hook";
import { KanbanRenderer } from "./kanban_renderer";

const { Component, useRef } = owl;

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
            onCreate: archInfo.onCreate,
            quickCreateView: archInfo.quickCreateView,
            defaultGroupBy,
            viewMode: "kanban",
            openGroupsByDefault: true,
            tooltipInfo: archInfo.tooltipInfo,
            rootState,
        });

        const rootRef = useRef("root");
        useViewButtons(this.model, rootRef);
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
        const { onCreate } = this.props.archInfo;
        const { root } = this.model;
        if (onCreate === "quick_create" && root.canQuickCreate()) {
            await root.quickCreate(group);
        } else if (onCreate && onCreate !== "quick_create") {
            await this.actionService.doAction(onCreate, { additionalContext: root.context });
        } else {
            await this.props.createRecord();
        }
    }

    get canCreate() {
        if (!this.model.root.isGrouped) {
            return this.props.archInfo.activeActions.create;
        }
        return !this.props.archInfo.activeActions.groupCreate || this.model.root.groups.length > 0;
    }
}

KanbanController.template = `web.KanbanView`;
KanbanController.components = { Layout, KanbanRenderer };
KanbanController.props = {
    ...standardViewProps,
    defaultGroupBy: { validate: (dgb) => !dgb || typeof dgb === "string", optional: true },
    editable: { type: Boolean, optional: true },
    forceGlobalClick: { type: Boolean, optional: true },
    hasSelectors: { type: Boolean, optional: true },
    onSelectionChanged: { type: Function, optional: true },
    showButtons: { type: Boolean, optional: true },
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
