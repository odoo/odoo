import { registry } from "@web/core/registry";
import { CompareImage } from "./compare_image";

const CompareImageEdit = (I) =>
    class extends I {
        /**
         * The "Initial position" option owns the divider in edit mode: a drag
         * could not be saved, since the editor ignores t-att-* writes.
         */
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
