import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import "@website/../tests/tours/pos_cta_button";

/*
 * @override of website tour to include eCommerce configuration steps
 */
patch(registry.category("web_tour.tours").get("pos_cta_button"), {
    steps() {
        const originalSteps = super.steps();
        const websiteBuildStepIndex = originalSteps.findIndex(
            (step) => step.id === "build_website"
        );
        originalSteps.splice(
            websiteBuildStepIndex + 1,
            0,
            {
                content: "Choose a shop page style",
                trigger: ".o_configurator_screen:contains(online catalog) .button_area",
                run: "click",
            },
            {
                content: "Choose a product page style",
                trigger: ".o_configurator_screen:contains(product page) .button_area",
                run: "click",
            }
        );
        return originalSteps;
    },
});
