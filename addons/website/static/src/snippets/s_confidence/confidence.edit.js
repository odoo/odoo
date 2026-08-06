import { registry } from "@web/core/registry";
import { Confidence } from "./confidence";

export const ConfidenceEdit = (I) =>
    class extends I {
        shouldStop() {
            return true;
        }
    };

registry.category("public.interactions.edit").add("website.confidence", {
    Interaction: Confidence,
    mixin: ConfidenceEdit,
});
registry.category("public.interactions.preview").add("website.confidence", {
    Interaction: Confidence,
    mixin: ConfidenceEdit,
});
