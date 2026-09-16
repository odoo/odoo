import { AbstractThirdPartyVideo } from "@html_editor/main/media/video/abstract_third_party_video";
import { encodeOptionsToParams, BooleanInt } from "@html_editor/main/media/video/utils";

export class Vimeo extends AbstractThirdPartyVideo {
    static id = "vimeo";
    static name = "Vimeo";

    static urlMatcher =
        /^(?:(?:https?:)?\/\/)?(player\.)?vimeo\.com\/(?:showcase\/|album\/)?(?:video\/)?(?<id>[^?#/]+)(?:\/(?:video\/)?(?<hash>[^?#/]+))?\/?(?:\?(?<params>\S+))?$/i;

    static optionsConfig = {
        startFrom: { default: 0, type: Number },
        autoplay: { default: false, type: BooleanInt, params: ["autoplay"] },
        muted: { default: false, type: BooleanInt, params: ["muted"] },
        loop: { default: false, type: BooleanInt, params: ["loop"] },
        hideControls: { default: false, type: BooleanInt, params: ["controls"], reversed: true },
    };

    /**
     * @override
     * @param {URL} url
     */
    static getCustomUrlOptions(url) {
        return {
            // Check if the pasted Vimeo URL is a Showcase or Album gallery (/showcase/ or /album/)
            isShowcase: url.pathname.includes("/showcase/") || url.pathname.includes("/album/"),
        };
    }

    /**
     * Returns the embed url for a vimeo video or showcase.
     *
     * @param {string} videoId
     * @param {Object} options
     * @return {string} url
     */
    static getEmbedUrl(videoId, options = {}) {
        const params = encodeOptionsToParams(options, Vimeo.optionsConfig);
        // Generates showcase embed URL (player.vimeo.com/showcase/.../embed) or standard video embed URL
        let embedUrl = options.isShowcase
            ? `https://player.vimeo.com/showcase/${videoId}/embed${params ? "?" + params : ""}`
            : `https://player.vimeo.com/video/${videoId}${params ? "?" + params : ""}`;
        if (options.startFrom) {
            embedUrl += `#t=${options.startFrom}`;
        }
        return embedUrl;
    }
    /**
     * Returns the url for the thumbnail image of the video.
     *
     * @param {string} videoId
     * @param {Object} [options={}]
     * @return {Promise<string>} url
     */
    static async getThumbnailUrl(videoId, options = {}) {
        if (options.isShowcase) {
            return "";
        }
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

    /**
     * Example urls are used to test that the urlMatcher regular expression
     * correctly identifies valid video urls and extracts the video ID.
     * Every urls in this object should be parsable by the urlMatcher.
     *
     * The `base` Url is also used in media dialog unit tests.
     *
     * @see /addons/html_editor/static/tests/media/*.test.js
     * */
    static exampleUrls = {
        base: "https://vimeo.com/395399735",
        unlisted: "https://vimeo.com/795669787/0763fdb816", // Not sure if this format is still relevant
        embed: "https://player.vimeo.com/video/395399735",
        embedUnlisted: "https://player.vimeo.com/video/795669787?h=0763fdb816",
        showcase: "https://vimeo.com/showcase/1234567",
        embedShowcase: "https://player.vimeo.com/showcase/1234567/embed",
        params: "vimeo.com/395399735?autoplay=1#t=62",
        embedParams:
            "https://player.vimeo.com/video/395399735?controls=0&autoplay=1#t=62",
    };
}
