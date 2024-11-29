import { charField, CharField } from "@web/views/fields/char/char_field";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

export class TourStartWidget extends CharField {
    static template = "web_tour.TourStartWidget";
    static props = {
        ...CharField.props,
        link: { type: Boolean, optional: true },
    };

    setup() {
        this.tour = useService("tour_service");
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
            stepDelay: 500,
            showPointerDuration: 250,
            rainbowManMessage: this.tourData.rainbow_man_message,
        });
    }
}

export const tourStartWidgetField = {
    ...charField,
    component: TourStartWidget,
    extractProps: ({ options }) => ({
        link: options.link,
    }),
};

registry.category("fields").add("tour_start_widget", tourStartWidgetField);
