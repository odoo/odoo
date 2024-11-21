import { registry } from "@web/core/registry";
import { RelationalModel } from "@web/model/relational_model/relational_model";
import { KanbanArchParser } from "./kanban_arch_parser";
import { KanbanCompiler } from "./kanban_compiler";
import { KanbanController } from "./kanban_controller";
import { KanbanRenderer } from "./kanban_renderer";

export const kanbanView = {
    type: "kanban",

    ArchParser: KanbanArchParser,
    Controller: KanbanController,
    Model: RelationalModel,
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
