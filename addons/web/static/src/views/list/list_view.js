// @ts-check

/** @module @web/views/list/list_view - List (tree) view descriptor registered in the view registry */

import { registry } from "@web/core/registry";
import { RelationalModel } from "@web/model/relational_model/relational_model";

import { ListArchParser } from "./list_arch_parser";
import { ListController } from "./list_controller";
import { ListRenderer } from "./list_renderer";

/**
 * View descriptor for the list (tree) view type.
 *
 * Registered in the "views" registry under the key "list". Wires together the
 * controller, renderer, arch parser, and relational model that make up the
 * standard list view.
 *
 * @type {import("@web/views/view").ViewDescriptor}
 */
export const listView = {
    type: "list",

    Controller: ListController,
    Renderer: ListRenderer,
    ArchParser: ListArchParser,
    Model: RelationalModel,

    buttonTemplate: "web.ListView.Buttons",

    canOrderByCount: true,

    /**
     * Build component props from generic view props and the view descriptor.
     *
     * Parses the arch XML via {@link ListArchParser} and merges the result
     * into the props passed to {@link ListController}.
     *
     * @param {Record<string, any>} genericProps - standard view props (arch, resModel, fields, etc.)
     * @param {typeof listView} view - the view descriptor
     * @returns {Record<string, any>} props for ListController
     */
    props: (genericProps, view) => {
        const { ArchParser } = view;
        const { arch, relatedModels, resModel } = genericProps;
        const archInfo = new ArchParser().parse(arch, relatedModels, resModel);
        return {
            ...genericProps,
            readonly: genericProps.readonly || !archInfo.activeActions?.edit,
            Model: view.Model,
            Renderer: view.Renderer,
            buttonTemplate: view.buttonTemplate,
            archInfo,
        };
    },
};

registry.category("views").add("list", listView);
