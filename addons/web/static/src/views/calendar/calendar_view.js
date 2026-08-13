import { registry } from "@web/core/registry";
import { CalendarRenderer } from "./calendar_renderer";
import { CalendarArchParser } from "./calendar_arch_parser";
import { CalendarModel } from "./calendar_model";
import { CalendarController } from "./calendar_controller";

export const calendarView = {
    type: "calendar",

    searchMenuTypes: ["filter", "favorite"],

    ArchParser: CalendarArchParser,
    Controller: CalendarController,
    Model: CalendarModel,
    Renderer: CalendarRenderer,

    buttonTemplate: "web.CalendarController.controlButtons",

    props: (props, view) => {
        const { ArchParser } = view;
        const { arch, relatedModels, resModel } = props;
        const archInfo = new ArchParser().parse(arch, relatedModels, resModel);
        return {
            ...props,
            Model: view.Model,
            Renderer: view.Renderer,
            buttonTemplate: view.buttonTemplate,
            archInfo,
        };
    },
};

registry.category("views").add("calendar", calendarView);
