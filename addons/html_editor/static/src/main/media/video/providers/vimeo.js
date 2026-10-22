import { AbstractThirdPartyVideo } from "@html_editor/main/media/video/abstract_third_party_video";
import { encodeOptionsToParams, BooleanInt } from "@html_editor/main/media/video/utils";

export class Vimeo extends AbstractThirdPartyVideo {
    static id = "vimeo";
    static name = "Vimeo";

    static urlMatcher =
        /^(?:(?:https?:)?\/\/)?(player.)?vimeo.com\/([a-z]*\/)?(?<id>[^?]+)(?:\/(?<hash>[^?]+))?(?:\?(?<params>\S+))?$/i;

    static optionsConfig = {
        startFrom: { default: 0, type: Number },
        autoplay: { default: false, type: BooleanInt, params: ["autoplay"] },
        muted: { default: false, type: BooleanInt, params: ["muted"] },
        loop: { default: false, type: BooleanInt, params: ["loop"] },
        hideControls: { default: false, type: BooleanInt, params: ["controls"], reversed: true },
        hideFullscreen: {
            default: false,
            type: BooleanInt,
            params: ["fullscreen"],
            reversed: true,
        },
    };
    /**
     * Returns the embed url for a vimeo video.
     *
     * @param {string} videoId
     * @param {Object} options
     * @return {string} url
     */
    static getEmbedUrl(videoId, options = {}) {
        const params = encodeOptionsToParams(options, Vimeo.optionsConfig);
        let embedUrl = `https://player.vimeo.com/video/${videoId}${params ? "?" + params : ""}`;
        if (options.startFrom) {
            embedUrl += `#t=${options.startFrom}`;
        }
        return embedUrl;
    }
    /**
     * Returns the url for the thumbnail image of the video.
     *
     * @param {string} videoId
     * @return {Promise[string]} url
     */
    static async getThumbnailUrl(videoId) {
        const apiResponse = await fetch(
            `https://vimeo.com/api/oembed.json?url=https://vimeo.com/${encodeURIComponent(videoId)}`
        );
        if (!apiResponse.ok) {
            console.warn(
                `Failed to fetch thumbnail for vimeo video ${videoId} with status ${apiResponse.status}`
            );
            return "";
        }
        const data = await apiResponse.json();
        return data.thumbnail_url || "";
    }
}
