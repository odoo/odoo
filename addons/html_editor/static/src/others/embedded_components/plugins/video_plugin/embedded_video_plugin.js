import { VideoPlugin } from "@html_editor/main/media/video_plugin";
import { _t } from "@web/core/l10n/translation";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { EmbeddedVideoSelector } from "./video_selector_dialog/embedded_video_selector";

/**
 * This plugin is meant to replace the Video plugin.
 */
export class EmbeddedVideoPlugin extends VideoPlugin {
    static id = "embeddedVideo";
    static dependencies = ["embeddedComponents", "media"];

    // Extends the base class resources
    resources = {
        ...this.resources,
        // Add a dedicated video powerbox item if inserting videos is available
        ...(this.config.allowVideo && {
            user_commands: {
                id: "openMediaDialogVideo",
                title: _t("Video"),
                description: _t("Insert a Video"),
                icon: "fa-play",
                run: () => this.dependencies.media.openMediaDialog({ activeTab: "VIDEOS" }),
                isAvailable: isHtmlContentSupported,
            },
            powerbox_items: {
                categoryId: "media",
                commandId: "openMediaDialogVideo",
            },
        }),
    };

    /** @override */
    get componentForMediaDialog() {
        return EmbeddedVideoSelector;
    }
}
