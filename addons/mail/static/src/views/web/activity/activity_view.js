import { ActivityArchParser } from "@mail/views/web/activity/activity_arch_parser";
import { ActivityController } from "@mail/views/web/activity/activity_controller";
import { ActivityModel } from "@mail/views/web/activity/activity_model";
import { ActivityRenderer } from "@mail/views/web/activity/activity_renderer";

import { registry } from "@web/core/registry";

export const activityView = {
    type: "activity",
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
