import { ZoomedBackgroundShape } from "./zoomed_background_shape";
import { registry } from "@web/core/registry";

const ZoomedBackgroundShapeEdit = (I) =>
    class extends I {
        shouldStop() {
            // Force restart.
            return true;
        }
    };

registry.category("public.interactions.edit").add("website.zoomed_background_shape", {
    Interaction: ZoomedBackgroundShape,
    mixin: ZoomedBackgroundShapeEdit,
});
