import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import "@point_of_sale/../tests/pos/tours/generic_tour";

patch(registry.category("web_tour.tours").get("generic_localization_tour"), {
    steps() {
        const originalSteps = super.steps();
        const stStep = originalSteps.findIndex(
            (step) => step.content === "feedback screen has finished the validation"
        );

        return [
            ...originalSteps.slice(0, stStep),
            {
                content: "Close the modal that appears with l10n_sa_edi_pos",
                trigger: `body`,
                async run({ waitFor, click }) {
                    const selector = `.modal:has(.modal-title:contains(zatca validation error))`;
                    const modal = await waitFor(selector, {
                        timeout: 9000,
                    }).catch(() => false);
                    if (modal) {
                        await click(`${selector} .btn:contains(ok)`);
                    }
                },
            },
            ...originalSteps.slice(stStep + 1),
        ];
    },
});
