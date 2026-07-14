import { registry } from "@web/core/registry";
import { RelationalModel } from "@web/model/relational_model/relational_model";
import { ListArchParser } from "./list_arch_parser";
import { ListController } from "./list_controller";
import { ListRenderer } from "./list_renderer";

export const listView = {
    type: "list",
    Controller: ListController,
    Renderer: ListRenderer,
    ArchParser: ListArchParser,
    Model: RelationalModel,
    buttonTemplate: "web.ListView.Buttons",
    canOrderByCount: true,

    limit: 80,

    props: (genericProps, view) => {
        const { ArchParser } = view;
        const { arch, relatedModels, resModel } = genericProps;
        const archInfo = new ArchParser().parse(arch, relatedModels, resModel);

        return {
            ...genericProps,
            Model: view.Model,
            Renderer: view.Renderer,
            buttonTemplate: view.buttonTemplate,
            archInfo,
        };
    },
};

registry.category("views").add("list", listView);
