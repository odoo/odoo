import { AbstractThirdPartyVideo } from "@html_editor/main/media/video/abstract_third_party_video";
import { encodeOptionsToParams, BooleanInt } from "@html_editor/main/media/video/utils";

export class Vimeo extends AbstractThirdPartyVideo {
    static id = "vimeo";
    static name = "Vimeo";

    static urlMatcher =
        /^(?:(?:https?:)?\/\/)?(player.)?vimeo.com\/([a-z]*\/)?(?<id>[^/?#]+)(?:\/(?<hash>[^/?#]+))?\/?(?:\?(?<params>\S+))?(?:#\S*)?$/i;

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
        // Privacy hash of unlisted videos.
        hash: { default: "", type: String, params: ["h"] },
    };
    /**
     * Returns the embed url for a vimeo video.
     *
     * @param {string} videoId
     * @param {Object} options
     * @return {string} url
     */
    static getEmbedUrl(videoId, options = {}) {
        let params = encodeOptionsToParams(options, Vimeo.optionsConfig);
        // "Do not track" is always enabled.
        params += `${params ? "&" : ""}dnt=1`;
        if (options.autoplay) {
            // Disabling autopause allows several autoplaying videos on a page
            // (e.g. background videos) to play simultaneously.
            params += "&autopause=0";
        }
        let embedUrl = `https://player.vimeo.com/video/${videoId}?${params}`;
        if (options.startFrom) {
            embedUrl += `#t=${options.startFrom}`;
        }
        return embedUrl;
    }
    /**
     * Returns the url for the thumbnail image of the video.
     *
     * @param {string} videoId
     * @param {Object} [options]
     * @return {Promise[string]} url
     */
    static async getThumbnailUrl(videoId, options = {}) {
        // Unlisted videos can only be found with their privacy hash.
        const videoPath = [videoId, options.hash].filter(Boolean).join("/");
        const videoUrl = encodeURIComponent(`https://vimeo.com/${videoPath}`);
        const apiResponse = await fetch(`https://vimeo.com/api/oembed.json?url=${videoUrl}`);
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
     * @override
     */
    static getCustomUrlOptions(url) {
        const options = {};
        // The privacy hash of unlisted videos can be part of the path (e.g.
        // `vimeo.com/<id>/<hash>`) instead of the `h` parameter.
        const hash = this.urlMatcher.exec(url.href)?.groups.hash;
        if (hash) {
            options.hash = hash;
        }
        // The start time is not a parameter but part of the fragment, in
        // seconds (e.g. `#t=62` or `#t=62s`) or not (e.g. `#t=1m2s`).
        const time = new URLSearchParams(url.hash.slice(1)).get("t");
        const [, hours = 0, minutes = 0, seconds = 0] =
            time?.match(/^(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s?)?$/) || [];
        const startFrom = hours * 3600 + minutes * 60 + Number(seconds);
        if (startFrom) {
            options.startFrom = startFrom;
        }
        return options;
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
        trailingSlash: "https://vimeo.com/395399735/",
        unlisted: "https://vimeo.com/795669787/0763fdb816",
        embed: "https://player.vimeo.com/video/395399735",
        embedUnlisted: "https://player.vimeo.com/video/795669787?h=0763fdb816",
        params: "vimeo.com/395399735?autoplay=1#t=62",
        embedParams:
            "https://player.vimeo.com/video/395399735?controls=0&fullscreen=1&autoplay=1#t=62",
    };
}
