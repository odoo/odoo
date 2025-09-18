// @ts-check

/** @module @web/views/kanban/kanban_view - Kanban view descriptor registered in the view registry */

import { registry } from "@web/core/registry";
import { RelationalModel } from "@web/model/relational_model/relational_model";

import { KanbanArchParser } from "./kanban_arch_parser";
import { KanbanCompiler } from "./kanban_compiler";
import { KanbanController } from "./kanban_controller";
import { KanbanRenderer } from "./kanban_renderer";

/**
 * Kanban view descriptor registered in the "views" registry.
 *
 * Wires together the arch parser, controller, model, renderer, and compiler
 * that collectively implement the kanban view type. The `props` factory parses
 * the arch XML and merges the result into the component props passed to the
 * controller.
 *
 * @type {{
 *   type: string,
 *   ArchParser: typeof KanbanArchParser,
 *   Controller: typeof KanbanController,
 *   Model: typeof RelationalModel,
 *   Renderer: typeof KanbanRenderer,
 *   Compiler: typeof KanbanCompiler,
 *   buttonTemplate: string,
 *   props: (genericProps: Object, view: Object) => Object,
 * }}
 */
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
        return {
            ...genericProps,
            readonly: genericProps.readonly || !archInfo.activeActions?.edit,
            Compiler: view.Compiler,
            Model: view.Model,
            Renderer: view.Renderer,
            buttonTemplate: view.buttonTemplate,
            archInfo,
        };
    },
};

registry.category("views").add("kanban", kanbanView);
