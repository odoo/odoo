import { Plugin } from "@html_editor/plugin";
import { VideoSelector } from "./media_dialog/video_selector";
import { _t } from "@web/core/l10n/translation";

export class VideoPlugin extends Plugin {
    static id = "video";
    static defaultConfig = {
        allowVideo: true,
    };
    resources = {
        ...(this.config.allowVideo && {
            media_dialog_extra_tabs: {
                id: "VIDEOS",
                title: _t("Videos"),
                Component: this.componentForMediaDialog,
                sequence: 30,
            },
        }),
    };

    get componentForMediaDialog() {
        return VideoSelector;
    }
}
