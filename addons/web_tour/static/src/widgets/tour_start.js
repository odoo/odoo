import { charField, CharField } from "@web/views/fields/char/char_field";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class TourStartWidget extends CharField {
    static template = "web_tour.TourStartWidget";
    static props = {
        ...CharField.props,
        link: { type: Boolean, optional: true },
    };

    setup() {
        this.tour = useService("tour_service");
        this.dialog = useService("dialog");
    }

    get tourData() {
        return this.props.record.data;
    }

    _launchManualTour() {
        this.tour.startTour(this.tourData.name, {
            mode: "manual",
            url: this.tourData.url,
            fromDB: this.tourData.custom,
            rainbowManMessage: this.tourData.rainbow_man_message,
        });
    }

    _launchAutomaticTour() {
        this.dialog.add(LaunchAutomaticTourDialog, {
            tour: this.tourData,
        });
    }
}

class LaunchAutomaticTourDialog extends Component {
    static template = "web_tour.LaunchAutomaticTourDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        tour: Object,
    };

    setup() {
        super.setup();
        this.tour = useService("tour_service");
    }

    async onConfirm() {
        this.tour.startTour(this.props.tour.name, {
            mode: "auto",
            url: this.props.tour.url,
            fromDB: this.props.tour.custom,
            showPointerDuration: 250,
            rainbowManMessage: this.props.tour.rainbow_man_message,
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
