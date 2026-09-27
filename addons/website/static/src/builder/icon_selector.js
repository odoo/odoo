import { IconSelector } from "@html_editor/main/media/media_dialog/icon_selector";
import { patch } from "@web/core/utils/patch";

patch(IconSelector, {
    mediaExtraClasses: [
        ...IconSelector.mediaExtraClasses,
        "rounded",
        "rounded-circle",
        "shadow",
        "img-thumbnail",
    ],
});
