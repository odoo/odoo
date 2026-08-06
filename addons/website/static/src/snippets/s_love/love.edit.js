import { registry } from "@web/core/registry";
import { Love } from "./love";

export const LoveEdit = (I) =>
    class extends I {
        shouldStop() {
            return true;
        }
    };

registry.category("public.interactions.edit").add("website.love", {
    Interaction: Love,
    mixin: LoveEdit,
});
registry.category("public.interactions.preview").add("website.love", {
    Interaction: Love,
    mixin: LoveEdit,
});
