import { MediaVideo } from "./media_video";
import { registry } from "@web/core/registry";

export const MediaVideoEdit = (I) =>
    class extends I {
        destroy() {
            // Destroy video iframes so they are never saved in the DOM.
            this.el?.replaceChildren();
        }
    };

registry.category("public.interactions.edit").add("website.media_video", {
    Interaction: MediaVideo,
    mixin: MediaVideoEdit,
});
