/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { GridArchParser } from "@web_grid/views/grid_arch_parser";
import { GridController } from "@web_grid/views/grid_controller";
import { GridRenderer } from "@web_grid/views/grid_renderer";
import { GridModel } from "@web_grid/views/grid_model";


export const gridView = {
    type: "grid",
    display_name: _t("Grid"),
    icon: "fa fa-th",
    multiRecord: true,
    ArchParser: GridArchParser,
    Controller: GridController,
    Model: GridModel,
    Renderer: GridRenderer,
    buttonTemplate: "web_grid.Buttons",

    props: (genericProps, view) => {
        const { ArchParser, Model, Renderer, buttonTemplate: viewButtonTemplate } = view;
        const { arch, relatedModels, resModel, buttonTemplate } = genericProps;
        return {
            ...genericProps,
            archInfo: new ArchParser().parse(arch, relatedModels, resModel),
            buttonTemplate: buttonTemplate || viewButtonTemplate,
            Model,
            Renderer,
        };
    }
};

registry.category('views').add('grid', gridView);
