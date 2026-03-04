import { AbstractThirdPartyVideo } from "@html_editor/main/media/video/abstract_third_party_video";
import { encodeOptionsToParams, BooleanInt } from "@html_editor/main/media/video/utils";

export class Youtube extends AbstractThirdPartyVideo {
    static id = "youtube";
    static name = "YouTube";

    static urlMatcher =
        /^(?:https?:\/\/)?(?:www\.|m\.)?(?:youtu\.be\/|youtube(-nocookie)?\.com\/(?:embed\/|v\/|shorts\/|live\/|watch\?v=|watch\?.+&v=))(?<id>(?:\w|-){11})\S*$/i;

    static optionsConfig = {
        startFrom: { default: 0, type: Number, params: ["start", "t"] },
        autoplay: { default: false, type: BooleanInt, params: ["autoplay"] },
        muted: { default: false, type: BooleanInt, params: ["mute"] },
        loop: { default: false, type: BooleanInt, params: ["loop"] },
        hideControls: { default: false, type: BooleanInt, params: ["controls"], reversed: true },
        hideFullscreen: { default: false, type: BooleanInt, params: ["fs"], reversed: true },
        isVertical: { default: false, type: Boolean },
        noCookie: { default: false, type: Boolean },
        enableJsApi: { default: false, type: BooleanInt, params: ["enablejsapi"] },
        showRelatedVideos: { default: true, type: BooleanInt, params: ["rel"] },
    };
    /**
     * Returns the embed url for a YouTube video.
     *
     * @param {string} videoId
     * @param {Object} options
     * @return {string} url
     */
    static getEmbedUrl(videoId, options = {}) {
        const noCookie = options.noCookie ? "-nocookie" : "";
        const params = encodeOptionsToParams(options, Youtube.optionsConfig);
        return `https://www.youtube${noCookie}.com/embed/${videoId}${params ? "?" + params : ""}`;
    }
    /**
     * Returns the url for the thumbnail image of the video.
     *
     * @param {string} videoId
     * @return {string} url
     */
    static getThumbnailUrl(videoId) {
        return `https://img.youtube.com/vi/${videoId}/0.jpg`;
    }
    /**
     * @override
     * @param {URL} url
     */
    static getCustomUrlOptions(url) {
        return {
            noCookie: url.hostname.includes("youtube-nocookie"),
            enableJsApi: true, // Always enable js api.
            showRelatedVideos: false, // Always disable related videos.
        };
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
        base: "https://www.youtube.com/watch?v=jar2eqeMNjc",
        short: "https://www.youtube.com/shorts/qAgW3oG7Zmc",
        live: "https://www.youtube.com/live/fmVNEoxr7iU?feature=shared",
        mobile: "https://m.youtube.com/watch?v=xCvFZrrQq7k",
        minified: "youtu.be/xCvFZrrQq7k",
        noCookie: "https://www.youtube-nocookie.com/watch?v=xCvFZrrQq7k",
        embed: "https://www.youtube.com/embed/xCvFZrrQq7k",
        params: "https://www.youtube.com/watch?v=xCvFZrrQq7k&t=62&autoplay=1&loop=1&controls=0&fs=0",
        embedParams:
            "https://www.youtube.com/embed/xCvFZrrQq7k?start=62&autoplay=1&loop=1&controls=0&fs=0",
    };
}
