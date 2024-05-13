import { registry } from "@web/core/registry";
import { RelationalModel } from "@web/model/relational_model/relational_model";
import { KanbanArchParser } from "./kanban_arch_parser";
import { KanbanCompiler } from "./kanban_compiler";
import { KanbanController } from "./kanban_controller";
import { KanbanRenderer } from "./kanban_renderer";

import { KanbanArchParser as KanbanArchParserLegacy } from "./kanban_arch_parser_legacy";

export const kanbanView = {
    type: "kanban",

    display_name: "Kanban",
    icon: "oi oi-view-kanban",
    multiRecord: true,

    ArchParser: KanbanArchParser,
    Controller: KanbanController,
    Model: RelationalModel,
    Renderer: KanbanRenderer,
    Compiler: KanbanCompiler,

    // TODO: remove post v18
    ArchParserLegacy: KanbanArchParserLegacy,

    buttonTemplate: "web.KanbanView.Buttons",

    props: (genericProps, view) => {
        const { arch, relatedModels, resModel } = genericProps;
        const isLegacyArch = !!arch.querySelector(`templates [t-name="kanban-box"]`);
        const ArchParser = isLegacyArch ? view.ArchParserLegacy : view.ArchParser;
        const archInfo = new ArchParser().parse(arch, relatedModels, resModel);
        const defaultGroupBy =
            genericProps.searchMenuTypes.includes("groupBy") && archInfo.defaultGroupBy;

        return {
            ...genericProps,
            // TODO: uncomment this
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
