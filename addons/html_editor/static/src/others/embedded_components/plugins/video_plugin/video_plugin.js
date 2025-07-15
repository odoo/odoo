import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { EmbeddedVideoSelector } from "./video_selector_dialog/embedded_video_selector";

export class VideoPlugin extends Plugin {
    static id = "video";
    static dependencies = ["embeddedComponents", "media"];
    static defaultConfig = {
        allowEmbeddedVideo: true,
    };
    // Only include the embedded video selector tab in the media dialog if it
    // doesn't already have the video tab.
    shouldIncludeEmbeddedVideoSelector =
        !this.config.allowMediaDialogVideo && this.config.allowEmbeddedVideo;
    resources = {
        ...(this.shouldIncludeEmbeddedVideoSelector && {
            media_dialog_extra_tabs: {
                id: "VIDEO",
                title: _t("Videos"),
                Component: EmbeddedVideoSelector,
                sequence: 30,
            },
            powerbox_items: {
                categoryId: "media",
                commandId: "openMediaDialogVideo",
            },
        }),
        // Add a dedicated video powerbox item if inserting videos is available
        ...((this.config.allowMediaDialogVideo || this.config.allowEmbeddedVideo) && {
            user_commands: [
                {
                    id: "openMediaDialogVideo",
                    title: _t("Video"),
                    description: _t("Insert a Video"),
                    icon: "fa-play",
                    run: () => this.dependencies.media.openMediaDialog({ activeTab: "VIDEO" }),
                    isAvailable: isHtmlContentSupported,
                },
            ],
            powerbox_items: {
                categoryId: "media",
                commandId: "openMediaDialogVideo",
            },
        }),
    };
}
