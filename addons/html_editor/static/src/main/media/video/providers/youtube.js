import { AbstractThirdPartyVideo } from "@html_editor/main/media/video/abstract_third_party_video";
import { encodeOptionsToParams, BooleanInt } from "@html_editor/main/media/video/utils";

export class Youtube extends AbstractThirdPartyVideo {
    static id = "youtube";
    static name = "YouTube";

    static urlMatcher =
        /^(?:https?:\/\/)?(?:www\.|m\.)?(?:youtu\.be\/|youtube(-nocookie)?\.com\/(?:embed\/(?!videoseries)|v\/|shorts\/|live\/|watch\?v=|watch\?.+&v=))(?<id>(?:\w|-){11})\S*$|^(?:https?:\/\/)?(?:www\.|m\.)?youtube(?:-nocookie)?\.com\/(?:playlist|embed\/videoseries)\?\S+$/i;

    static optionsConfig = {
        startFrom: { default: 0, type: Number, params: ["start", "t"] },
        autoplay: { default: false, type: BooleanInt, params: ["autoplay"] },
        muted: { default: false, type: BooleanInt, params: ["mute"] },
        loop: { default: false, type: BooleanInt, params: ["loop"] },
        hideControls: { default: false, type: BooleanInt, params: ["controls"], reversed: true },
        hideFullscreen: { default: false, type: BooleanInt, params: ["fs"], reversed: true },
        isVertical: { default: false, type: Boolean },
        noCookie: { default: false, type: Boolean },
        // `list`: Query parameter for YouTube Playlist IDs (e.g. ?list=PL4fGSI...)
        list: { default: "", type: String, params: ["list"] },
        // `playlist`: YouTube API quirk requiring VIDEO_ID to loop a single video (?loop=1&playlist=VIDEO_ID)
        playlist: { default: "", type: String, linkedParams: ["playlist"] },
        enableJsApi: { default: false, type: BooleanInt, params: ["enablejsapi"] },
        showRelatedVideos: { default: true, type: BooleanInt, params: ["rel"] },
    };

    /**
     * @override
     */
    static isValidVideoUrl(url) {
        const match = super.isValidVideoUrl(url);
        if (!match) {
            return false;
        }
        const hasId = !!match.groups?.id;
        const normalizedUrl = url.trim().startsWith("http") ? url.trim() : "https://" + url.trim();
        const hasList = URL.canParse(normalizedUrl) && new URL(normalizedUrl).searchParams.has("list");
        // A YouTube URL is valid if it contains either a Video ID or a Playlist ID.
        if (!hasId && !hasList) {
            return false;
        }
        return match;
    }

    /**
     * Returns the embed url for a YouTube video or playlist.
     *
     * @param {string} videoId
     * @param {Object} options
     * @return {string} url
     */
    static getEmbedUrl(videoId, options = {}) {
        const noCookie = options.noCookie ? "-nocookie" : "";
        // Single videos require playlist=VIDEO_ID to loop. Actual playlists (options.list) loop naturally.
        if (options.loop && !options.list && videoId) {
            options.playlist = videoId;
        }
        const params = encodeOptionsToParams(options, Youtube.optionsConfig);
        // Pure playlists without a single video ID use YouTube's 'videoseries' endpoint
        const embedId = videoId || (options.list ? "videoseries" : "");
        return `https://www.youtube${noCookie}.com/embed/${embedId}${params ? "?" + params : ""}`;
    }
    /**
     * Returns the url for the thumbnail image of the video.
     *
     * @param {string} videoId
     * @param {Object} [options={}]
     * @return {string} url
     */
    static getThumbnailUrl(videoId, options = {}) {
        // Static thumbnail CDN URLs exist only for single video IDs, not for pure playlists or 'videoseries'.
        return videoId && !options.list
            ? `https://img.youtube.com/vi/${videoId}/0.jpg`
            : "";
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
        playlist: "https://www.youtube.com/playlist?list=PL4fGSI1pDJn6O1LS0XSdF3RyO0Rq_LDeI",
        embedPlaylist: "https://www.youtube.com/embed/videoseries?list=PL4fGSI1pDJn6O1LS0XSdF3RyO0Rq_LDeI",
        params: "https://www.youtube.com/watch?v=xCvFZrrQq7k&t=62&autoplay=1&loop=1&controls=0&fs=0",
        embedParams:
            "https://www.youtube.com/embed/xCvFZrrQq7k?start=62&autoplay=1&loop=1&controls=0&fs=0",
    };
}
