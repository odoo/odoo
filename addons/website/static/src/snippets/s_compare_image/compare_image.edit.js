import { registry } from "@web/core/registry";
import { CompareImage } from "./compare_image";

const CompareImageEdit = (I) =>
    class extends I {
        /**
         * In edit mode the divider position is owned by the "Initial position"
         * option, so the on-page handle must not move. A drag here would be
         * applied through t-att-style, which the editor ignores and reverts on
         * destroy, so it could never be saved and would silently disagree with
         * the value shown in the sidebar.
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
