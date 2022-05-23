/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { Layout } from "@web/search/layout";
import { usePager } from "@web/search/pager_hook";
import { useModel } from "@web/views/helpers/model";
import { standardViewProps } from "@web/views/helpers/standard_view_props";
import { useSetupView } from "@web/views/helpers/view_hook";
import { useViewButtons } from "@web/views/view_button/hook";
import { KanbanRenderer } from "./kanban_renderer";

const { Component, useRef } = owl;

// -----------------------------------------------------------------------------

export class KanbanController extends Component {
    setup() {
        this.actionService = useService("action");
        this.model = useModel(this.props.Model, this.props.modelParams);

        const rootRef = useRef("root");
        useViewButtons(this.model, rootRef);
        useSetupView({ rootRef /** TODO **/ });
        usePager(() => {
            if (!this.model.root.isGrouped) {
                return {
                    offset: this.model.root.offset,
                    limit: this.model.root.limit,
                    total: this.model.root.count,
                    onUpdate: async ({ offset, limit }) => {
                        this.model.root.offset = offset;
                        this.model.root.limit = limit;
                        await this.model.root.load();
                        this.render(true); // FIXME WOWL reactivity
                    },
                };
            }
        });
    }

    async openRecord(record, mode) {
        const activeIds = this.model.root.records.map((datapoint) => datapoint.resId);
        this.props.selectRecord(record.resId, { activeIds, mode });
    }

    async createRecord(group) {
        const { onCreate } = this.props.archInfo;
        const { root } = this.model;
        if (root.canQuickCreate()) {
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
    Model: Function,
    modelParams: Object,
    Renderer: Function,
    buttonTemplate: String,
    archInfo: Object,
};

KanbanController.defaultProps = {
    createRecord: () => {},
    selectRecord: () => {},
};
