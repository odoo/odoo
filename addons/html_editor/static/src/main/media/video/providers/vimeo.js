import { AbstractThirdPartyVideo } from "@html_editor/main/media/video/abstract_third_party_video";
import { encodeOptionsToParams, BooleanInt } from "@html_editor/main/media/video/utils";

export class Vimeo extends AbstractThirdPartyVideo {
    static id = "vimeo";
    static name = "Vimeo";

    static urlMatcher =
        /^(?:(?:https?:)?\/\/)?(?:player\.)?vimeo\.com\/(?:(?<showcase>showcase|album)\/|video\/)?(?<id>\d+)(?:\/(?<hash>[\da-f]+))?(?:[/?#]\S*)?$/i;

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
        isVertical: { default: false, type: Boolean },
        privacyHash: { default: "", type: String, params: ["h"] },
    };
    /**
     * @override
     * @param {URL} url
     * @param {RegExpExecArray} urlMatch
     */
    static getCustomUrlOptions(url, urlMatch) {
        // e.g. "#t=62" (see getEmbedUrl) or "#t=1h2m3s"
        const time = url.hash.match(/^#t=(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s?)?$/);
        return {
            isShowcase: !!urlMatch.groups.showcase,
            ...(urlMatch.groups.hash && { privacyHash: urlMatch.groups.hash }),
            ...(time && {
                startFrom:
                    parseInt(time[1] || 0) * 3600 +
                    parseInt(time[2] || 0) * 60 +
                    parseInt(time[3] || 0),
            }),
        };
    }
    /**
     * Returns the embed url for a vimeo video.
     *
     * @param {string} videoId
     * @param {Object} options
     * @return {string} url
     */
    static getEmbedUrl(videoId, options = {}) {
        const params = encodeOptionsToParams(options, Vimeo.optionsConfig);
        if (options.isShowcase) {
            // A showcase has no start time: "#t=" stops its autoplay.
            return `https://vimeo.com/showcase/${videoId}/embed${params ? "?" + params : ""}`;
        }
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
     * @param {Object} options
     * @return {Promise[string]} url
     */
    static async getThumbnailUrl(videoId, options = {}) {
        const showcase = options.isShowcase ? "showcase/" : "";
        const apiResponse = await fetch(
            `https://vimeo.com/api/oembed.json?url=https://vimeo.com/${showcase}${encodeURIComponent(
                videoId
            )}`
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
        unlisted: "https://vimeo.com/795669787/0763fdb816",
        embed: "https://player.vimeo.com/video/395399735",
        embedUnlisted: "https://player.vimeo.com/video/795669787?h=0763fdb816",
        embedStartFrom: "https://player.vimeo.com/video/395399735#t=62",
        showcase: "https://vimeo.com/showcase/1000",
        album: "https://vimeo.com/album/1000",
        embedShowcase: "https://vimeo.com/showcase/1000/embed2",
        params: "vimeo.com/395399735?autoplay=1#t=62",
        embedParams:
            "https://player.vimeo.com/video/395399735?controls=0&fullscreen=1&autoplay=1#t=62",
    };
}
