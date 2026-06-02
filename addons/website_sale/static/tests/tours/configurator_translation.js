import { registry } from '@web/core/registry';
import { patch } from '@web/core/utils/patch';
import '@website/../tests/tours/configurator_translation';

/*
 * @override of website tour to include eCommerce configuration steps
 */
patch(registry.category('web_tour.tours').get('configurator_translation'), {

    steps() {
        const originalSteps = super.steps();
        const loaderStepIndex = originalSteps.findIndex(
            (step) => step.id === 'loader'
        );
        if (loaderStepIndex === -1) {
            return originalSteps;
        }
        originalSteps.splice(
            loaderStepIndex,
            0,
            {
                content: "Choose a shop page style",
                trigger: '.o_configurator_screen:contains(online catalog) .button_area',
                run: 'click',
            },
            {
                content: "Choose a product page style",
                trigger: '.o_configurator_screen:contains(product page) .button_area',
                run: 'click',
            },
        );
        return originalSteps;
    },

});
/*
 * @override of website tour to include eCommerce configuration steps
 */
patch(registry.category("web_tour.tours").get("configurator_page_creation"), {
    steps() {
        const originalSteps = super.steps();
        const loaderStepIndex = originalSteps.findIndex(
            (step) => step.id === "loader"
        );
        if (loaderStepIndex === -1) {
            return originalSteps;
        }
        originalSteps.splice(
            loaderStepIndex,
            0,
            {
                content: "Choose a shop page style",
                trigger: ".o_configurator_screen:contains('online catalog') .button_area",
                run: "click",
            },
            {
                content: "Choose a product page style",
                trigger: ".o_configurator_screen:contains('product page') .button_area",
                run: "click",
            }
        );
        return originalSteps;
    },
});
