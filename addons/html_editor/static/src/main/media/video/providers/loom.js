import { AbstractThirdPartyVideo } from "@html_editor/main/media/video/abstract_third_party_video";
import { encodeOptionsToParams, BooleanInt } from "@html_editor/main/media/video/utils";

export class Loom extends AbstractThirdPartyVideo {
    static id = "loom";
    static name = "Loom";

    static urlMatcher =
        /^https:\/\/(?:www\.)?loom\.com\/(?:embed|share)\/(?<id>[0-9a-z]+)\\?(?:[?&]([0-9a-zA-Z_]+)=([0-9a-zA-Z_-]+))*$/i;

    static optionsConfig = {
        startFrom: { default: 0, type: Number, params: ["t"] },
        autoplay: { default: false, type: BooleanInt, params: ["autoplay"] },
        muted: { default: false, type: BooleanInt, params: ["muted"] },
        hideControls: {
            default: false,
            type: BooleanInt,
            params: ["hideEmbedTopBar"],
            linkedParams: ["hide_share", "hide_title", "hide_owner", "hide_speed"],
            reversed: true,
        },
        hideFullscreen: {
            default: false,
            type: BooleanInt,
            params: ["fullscreen"],
            reversed: true,
        },
    };
    /**
     * Returns the embed url for a loom video.
     *
     * @param {string} videoId
     * @param {Object} options
     * @return {string} url
     */
    static getEmbedUrl(videoId, options = {}) {
        const params = encodeOptionsToParams(options, Loom.optionsConfig);
        return `https://www.loom.com/embed/${videoId}${params ? "?" + params : ""}`;
    }
}
