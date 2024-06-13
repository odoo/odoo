import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import ToursDialog from "@web_tour/debug/tour_dialog_component";
import { useState, useRef } from "@odoo/owl";
import { downloadFile } from "@web/core/network/download";

/**
 * @typedef {import("@web_tour/tour_service/tour_service").Tour} Tour
 */

patch(ToursDialog, {
    components: { ...ToursDialog.components, Dropdown, DropdownItem },
});

patch(ToursDialog.prototype, {
    setup() {
        super.setup();
        this.tourRecorder = useService("tour_recorder");
        this.notification = useService("notification");
        this.state = useState({
            customTours: this.tourRecorder.getCustomTours(),
        });
        this.importTourInput = useRef("import_tour_input");
    },

    /**
     * @param {MouseEvent} ev
     */
    onStartCustomTour(ev) {
        this.tourRecorder.startCustomTour(ev.target.dataset.name, { mode: "manual" });
        this.props.close();
    },
    /**
     * @param {MouseEvent} ev
     */
    onTestCustomTour(ev) {
        this.tourRecorder.startCustomTour(ev.target.dataset.name, {
            mode: "auto",
            stepDelay: 500,
            showPointerDuration: 250,
        });
        this.props.close();
    },

    /**
     *
     * @param {Tour} customTour
     */
    deleteTour(customTour) {
        const tourIndex = this.state.customTours.indexOf(customTour);
        this.state.customTours.splice(tourIndex, 1);
        this.tourRecorder.removeCustomTour(customTour);
    },

    /**
     * @param {InputEvent} ev
     */
    async importTour(ev) {
        if (!ev.target.files.length) {
            return;
        }

        const fileText = await ev.target.files[0].text();
        const customTour = JSON.parse(fileText);
        const result = this.tourRecorder.addCustomTour(customTour);
        if (result) {
            this.state.customTours = this.tourRecorder.getCustomTours();
        }
    },

    /**
     * @param {Tour} tour
     */
    exportTourJSON(tour) {
        downloadFile(
            JSON.stringify({
                ...tour,
                wait_for: undefined,
                steps: tour.steps.map((s) => {
                    return {
                        ...s,
                        state: undefined,
                    };
                }),
            }),
            tour.name,
            "application/json"
        );
    },

    /**
     * @param {Tour} tour
     */
    exportTourJS(tour) {
        downloadFile(
            `import { registry } from '@web/core/registry';

registry.category("web_tour.tours").add("${tour.name}", {
    url: "${tour.url}",
    steps: () => ${JSON.stringify(
        tour.steps.map((s) => {
            return {
                ...s,
                state: undefined,
            };
        }),
        null,
        4
    )},
});`,
            tour.name,
            "application/javascript"
        );
    },
});
