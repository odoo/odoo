import { MediaVideo } from "./media_video";
import { registry } from "@web/core/registry";

registry
    .category("public.interactions.edit")
    .add("website.media_video", {
        Interaction: MediaVideo,
    });
