import { registry } from '@web/core/registry';
import { patch } from '@web/core/utils/patch';
import '@website/../tests/tours/configurator_translation';

/*
 * @override of website tour to include eCommerce configuration steps
 */
patch(registry.category('web_tour.tours').get('configurator_translation'), {

    steps() {
        const originalSteps = super.steps();
        const websiteBuildStepIndex = originalSteps.findIndex(
            (step) => step.id === 'build_website'
        );
        originalSteps.splice(
            websiteBuildStepIndex + 1,
            0,
            {
                content: "Choose a shop page style",
                trigger: '.theme_preview',
                run: 'click',
            },
            {
                content: "Choose a product page style",
                trigger: '.theme_preview',
                run: 'click',
            },
        );
        return originalSteps;
    },

});
