/** @odoo-module **/

import { registry } from "@web/core/registry";
import { KanbanController } from "./kanban_controller";
import { KanbanModel } from "./kanban_model";
import { KanbanArchParser } from "./kanban_arch_parser";
import { KanbanRenderer } from "./kanban_renderer";

export const kanbanView = {
    type: "kanban",
    display_name: "Kanban",
    icon: "oi oi-view-kanban",
    multiRecord: true,
    Controller: KanbanController,
    Renderer: KanbanRenderer,
    Model: KanbanModel,
    ArchParser: KanbanArchParser,
    buttonTemplate: "web.KanbanView.Buttons",

    props: (genericProps, view) => {
        const { ArchParser } = view;
        const { arch, fields, resModel, limit, searchMenuTypes } = genericProps;
        const archInfo = new ArchParser().parse(arch, fields);
        const { activeFields, defaultGroupBy, onCreate, quickCreateView } = archInfo;
        const modelParams = {
            activeFields,
            progressAttributes: archInfo.progressAttributes,
            fields,
            resModel,
            limit: archInfo.limit || limit,
            onCreate,
            quickCreateView,
            defaultGroupBy: searchMenuTypes.includes("groupBy") && defaultGroupBy,
            viewMode: "kanban",
            openGroupsByDefault: true,
            tooltipInfo: archInfo.tooltipInfo,
        };

        return {
            ...genericProps,
            Model: view.Model,
            modelParams,
            Renderer: view.Renderer,
            buttonTemplate: view.buttonTemplate,
            archInfo,
        };
    },
};

registry.category("views").add("kanban", kanbanView);
