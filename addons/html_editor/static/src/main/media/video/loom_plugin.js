import { _t } from "@web/core/l10n/translation";
import { ThirdPartyVideoAbstract } from "@html_editor/main/media/video/third_party_video_abstract";

export const LOOM_URL_GET_VIDEO_ID = /https:\/\/(?:www\.)?loom\.com\/[a-z]+\/([0-9a-z]+)$/i;

export class LoomPlugin extends ThirdPartyVideoAbstract {
    static id = "loom";

    /**
     * @param {string} url
     */
    getCommandForVideoUrlPaste(url) {
        const videoUrl = LOOM_URL_GET_VIDEO_ID.exec(url);
        if (videoUrl) {
            return {
                title: _t("Embed Loom Video"),
                description: _t("Embed the video in the document."),
                icon: "fa-play-circle",
                run: () => this.insertVideoElement(videoUrl[0]),
            };
        }
    }
}
