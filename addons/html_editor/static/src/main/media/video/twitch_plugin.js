import { _t } from "@web/core/l10n/translation";
import { ThirdPartyVideoAbstract } from "@html_editor/main/media/video/third_party_video_abstract";

export const TWITCH_URL_GET_VIDEO_ID =
    /^https:\/\/(?:www\.)?twitch\.tv\/(?:videos|(?:[0-9a-z_]{4,25}\/clip))\/([0-9a-z_-]+)$/i;

export class TwitchPlugin extends ThirdPartyVideoAbstract {
    static id = "twitch";

    /**
     * @param {string} url
     */
    getCommandForVideoUrlPaste(url) {
        const videoUrl = TWITCH_URL_GET_VIDEO_ID.exec(url);
        if (videoUrl) {
            return {
                title: _t("Embed Twitch Video"),
                description: _t("Embed the video in the document."),
                icon: "fa-play-circle",
                run: () => this.insertVideoElement(videoUrl[0]),
            };
        }
    }
}
