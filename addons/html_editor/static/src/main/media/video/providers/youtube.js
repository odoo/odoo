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
        playlist: { default: "", type: String, linkedParams: ["playlist"] },
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
        if (options.loop) {
            options.playlist = videoId;
        }
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
}
