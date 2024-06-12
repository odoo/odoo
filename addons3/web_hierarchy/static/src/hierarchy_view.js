/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { HierarchyArchParser } from "./hierarchy_arch_parser";
import { HierarchyController } from "./hierarchy_controller";
import { HierarchyModel } from "./hierarchy_model";
import { HierarchyRenderer } from "./hierarchy_renderer";

export const hierarchyView = {
    type: "hierarchy",
    display_name: _t("Hierarchy"),
    icon: "fa fa-share-alt o_hierarchy_icon",
    isMobileFriendly: false,
    multiRecord: true,
    ArchParser: HierarchyArchParser,
    Controller: HierarchyController,
    Model: HierarchyModel,
    Renderer: HierarchyRenderer,
    buttonTemplate: "web_hierarchy.HierarchyButtons",
    searchMenuTypes: [],

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
}

registry.category("views").add("hierarchy", hierarchyView);
