/** @odoo-module */

import { registry } from "@web/core/registry";
import { ActivityController } from "./activity_controller";
import { ActivityRenderer } from "./activity_renderer";
import { ActivityModel } from "./activity_model";
import { ActivityArchParser } from "./activity_arch_parser";

export const activityView = {
    type: "activity",
    display_name: "Activity",
    icon: "fa fa-clock-o",
    multiRecord: true,
    searchMenuTypes: ["filter", "favorite"],
    Controller: ActivityController,
    Renderer: ActivityRenderer,
    ArchParser: ActivityArchParser,
    Model: ActivityModel,
    props: (genericProps, view) => {
        const { arch, relatedModels, resModel } = genericProps;
        const archInfo = new view.ArchParser().parse(arch, relatedModels, resModel);
        return {
            ...genericProps,
            archInfo,
            Model: view.Model,
            Renderer: view.Renderer,
        };
    },
};
registry.category("views").add("activity", activityView);
