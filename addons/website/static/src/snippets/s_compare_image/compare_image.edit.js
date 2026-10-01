import { registry } from "@web/core/registry";
import { CompareImage } from "./compare_image";

const CompareImageEdit = (I) =>
    class extends I {
        onPointerDown() {}

        /**
         * Nothing to write: the position comes from the inline style the option
         * sets on the root, which the stylesheet already reads directly.
         */
        get rootStyle() {
            return {};
        }
    };

registry.category("public.interactions.edit").add("website.compare_image", {
    Interaction: CompareImage,
    mixin: CompareImageEdit,
});
