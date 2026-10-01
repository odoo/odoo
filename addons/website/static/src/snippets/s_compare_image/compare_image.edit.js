import { registry } from "@web/core/registry";
import { CompareImage } from "./compare_image";

const CompareImageEdit = (I) =>
    class extends I {
        setup() {
            super.setup();
            this.websiteEditService = this.services.website_edit;
        }

        /**
         * Disables the frontend's t-att-style write: the editor applies those
         * inside an ignored observer callback and reverts them on destroy, so
         * they can neither be saved nor survive a restart.
         */
        get rootStyle() {
            return {};
        }

        onPointerMove(ev) {
            super.onPointerMove(ev);
            // A real inline style, so the editor's observer records it and the
            // dragged position is part of what gets saved.
            this.el.style.setProperty("--compare-pos", `${this.position}%`);
        }

        stopDragging(ev) {
            const wasDragging = this.isDragging;
            super.stopDragging(ev);
            if (wasDragging) {
                // Mutations accumulate until committed, so the whole gesture
                // lands as a single undoable step rather than one per frame.
                this.websiteEditService.callShared("history", "commit");
            }
        }
    };

registry.category("public.interactions.edit").add("website.compare_image", {
    Interaction: CompareImage,
    mixin: CompareImageEdit,
});
