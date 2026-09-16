import { AbstractThirdPartyVideo } from "@html_editor/main/media/video/abstract_third_party_video";
import { encodeOptionsToParams, BooleanInt } from "@html_editor/main/media/video/utils";

export class Dailymotion extends AbstractThirdPartyVideo {
    static id = "dailymotion";
    static name = "Dailymotion";
    static urlMatcher =
        /^(https?:\/\/)(www\.)?(dailymotion\.com\/(embed\/video\/|embed\/playlist\/|embed\/|video\/|playlist\/|hub\/.*#video=)|geo\.dailymotion\.com\/player\.html\?(?:video|playlist)=|dai\.ly\/)(?<id>[A-Za-z0-9]{6,7})(?:[-_][-_a-z]*)?(?:[?&=](?:[0-9a-z]+))*$/i;

    static optionsConfig = {
        startFrom: { default: 0, type: Number, params: ["startTime"] },
        // Added supported Dailymotion parameters: autoplay, mute (when autoplay is enabled), and controls toggle
        autoplay: { default: false, type: BooleanInt, params: ["autoplay"] },
        muted: { default: false, type: BooleanInt, params: ["mute"] },
        hideControls: { default: false, type: BooleanInt, params: ["controls"], reversed: true },
    };

    /**
     * @override
     * @param {URL} url
     */
    static getCustomUrlOptions(url) {
        return {
            // Checks if the Dailymotion link is a playlist (contains /playlist/ in pathname or ?playlist= in query)
            isPlaylist: url.pathname.includes("/playlist/") || url.searchParams.has("playlist"),
        };
    }

    /**
     * Returns the embed url for a dailymotion video or playlist.
     *
     * @param {string} videoId
     * @param {Object} options
     * @return {string} url
     */
    static getEmbedUrl(videoId, options = {}) {
        const params = encodeOptionsToParams(options, Dailymotion.optionsConfig);
        // Switches query parameter between 'playlist' (for playlists) and 'video' (for single videos)
        const queryParam = options.isPlaylist ? "playlist" : "video";
        return `https://geo.dailymotion.com/player.html?${queryParam}=${videoId}${
            params ? "&" + params : ""
        }`;
    }
    /**
     * Returns the url for the thumbnail image of the video.
     *
     * @param {string} videoId
     * @param {Object} [options={}]
     * @return {string} url
     */
    static getThumbnailUrl(videoId, options = {}) {
        return options.isPlaylist ? "" : `https://www.dailymotion.com/thumbnail/video/${videoId}`;
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
        base: "https://www.dailymotion.com/video/x7svr6t",
        extra: "https://www.dailymotion.com/video/x2jvvep_hakan-yukur-klip_sport",
        embed: "https://geo.dailymotion.com/player.html?video=x7svr6t",
        minified: "dai.ly/x7svr6t",
        playlist: "https://www.dailymotion.com/playlist/x61w5b",
        embedPlaylist: "https://geo.dailymotion.com/player.html?playlist=x61w5b",
        params: "https://www.dailymotion.com/video/x7svr6t?startTime=62",
        embedParams: "https://geo.dailymotion.com/player.html?video=x7svr6t&startTime=62",
        // This is the old embed url of dailymotion,
        // we keep supporting it for backward compatibility reasons,
        // but it should not be used anymore.
        dailymotion_old_embed: "https://www.dailymotion.com/embed/video/x578has?autoplay=1",
    };
}
