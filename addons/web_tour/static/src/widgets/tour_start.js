import { useProps, t, usePlugin } from "@odoo/owl";
import { charField, CharField, charFieldProps } from "@web/views/fields/char/char_field";
import { registry } from "@web/core/registry";
import { TourPlugin } from "@web_tour/tour_plugin";

export class TourStartWidget extends CharField {
    static template = "web_tour.TourStartWidget";
    props = useProps({
        ...charFieldProps,
        link: t.boolean().optional(),
    });

    setup() {
        this.tour = usePlugin(TourPlugin);
    }

    get tourData() {
        return this.props.record.data;
    }

    _onStartTour() {
        this.tour.startTour(this.tourData.name, {
            mode: "manual",
            url: this.tourData.url,
            fromDB: this.tourData.custom,
            rainbowManMessage: this.tourData.rainbow_man_message,
        });
    }

    _onTestTour() {
        this.tour.startTour(this.tourData.name, {
            mode: "auto",
            url: this.tourData.url,
            fromDB: this.tourData.custom,
            showPointerDuration: 250,
            rainbowManMessage: this.tourData.rainbow_man_message,
        });
    }
}

export const tourStartWidgetField = {
    ...charField,
    component: TourStartWidget,
    extractProps: ({ viewType }) => ({
        link: viewType === "list",
    }),
};

registry.category("fields").add("tour_start_widget", tourStartWidgetField);
