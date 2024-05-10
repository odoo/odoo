import { registry } from "@web/core/registry";
import { RelationalModel } from "@web/model/relational_model/relational_model";
import { KanbanArchParser } from "./kanban_arch_parser";
import { KanbanCompiler } from "./kanban_compiler";
import { KanbanController } from "./kanban_controller";
import { KanbanRecord } from "./kanban_record";
import { KanbanRenderer } from "./kanban_renderer";

import { KanbanArchParser as KanbanArchParserLegacy } from "./kanban_arch_parser_legacy";
import { KanbanCompiler as KanbanCompilerLegacy } from "./kanban_compiler_legacy";
import { KanbanRecord as KanbanRecordLegacy } from "./kanban_record_legacy";

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
    Record: KanbanRecord,

    // TODO: remove post v18
    ArchParserLegacy: KanbanArchParserLegacy,
    CompilerLegacy: KanbanCompilerLegacy,
    RecordLegacy: KanbanRecordLegacy,

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
            Compiler: isLegacyArch ? view.CompilerLegacy : view.Compiler,
            Model: view.Model,
            Renderer: view.Renderer,
            Record: isLegacyArch ? view.RecordLegacy : view.Record,
            buttonTemplate: view.buttonTemplate,
            archInfo,
            defaultGroupBy,
        };
    },
};

registry.category("views").add("kanban", kanbanView);
