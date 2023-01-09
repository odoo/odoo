/** @odoo-module **/

import { KanbanArchParser } from "./kanban_arch_parser";
import { KanbanCompiler } from "./kanban_compiler";
import { KanbanController } from "./kanban_controller";
import { KanbanModel } from "./kanban_model";
import { KanbanRenderer } from "./kanban_renderer";
import { registry } from "@web/core/registry";

export const kanbanView = {
    type: "kanban",

    display_name: "Kanban",
    icon: "oi oi-view-kanban",
    isMobileFriendly: true,
    multiRecord: true,

    ArchParser: KanbanArchParser,
    Controller: KanbanController,
    Model: KanbanModel,
    Renderer: KanbanRenderer,
    Compiler: KanbanCompiler,

    buttonTemplate: "web.KanbanView.Buttons",

    props: (genericProps, view) => {
        const { arch, relatedModels, resModel } = genericProps;
        const { ArchParser } = view;
        const archInfo = new ArchParser().parse(arch, relatedModels, resModel);
        const defaultGroupBy =
            genericProps.searchMenuTypes.includes("groupBy") && archInfo.defaultGroupBy;

        return {
            ...genericProps,
            // Compiler: view.Compiler, // don't pass it automatically in stable, for backward compat
            Model: view.Model,
            Renderer: view.Renderer,
            buttonTemplate: view.buttonTemplate,
            archInfo,
            defaultGroupBy,
        };
    },
};

registry.category("views").add("kanban", kanbanView);
