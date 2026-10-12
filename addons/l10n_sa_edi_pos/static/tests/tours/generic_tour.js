import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import "@point_of_sale/../tests/pos/tours/generic_tour";

patch(registry.category("web_tour.tours").get("generic_localization_tour"), {
    steps() {
        const originalSteps = super.steps();
        const stStep = originalSteps.findIndex(
            (step) => step.content === "feedback screen has finished the validation"
        );

        const modal = `.modal:has(.modal-title:contains(zatca validation error))`;
        return [
            ...originalSteps.slice(0, stStep),
            {
                content: "close the ZATCA modal if it shows before the validation finishes",
                timeout: 20000,
                trigger: `${modal}, .feedback-screen .button.validation:not([disabled])`,
                async run({ anchor, click }) {
                    if (anchor.closest(".modal")) {
                        await click(`${modal} .btn:contains(ok)`);
                    }
                },
            },
            ...originalSteps.slice(stStep + 1),
        ];
    },
});
