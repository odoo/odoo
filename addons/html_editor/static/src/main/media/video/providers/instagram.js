import { AbstractThirdPartyVideo } from "@html_editor/main/media/video/abstract_third_party_video";

export class Instagram extends AbstractThirdPartyVideo {
    static id = "instagram";
    static name = "Intagram";

    static urlMatcher =
        /^(?:https?:\/\/)?(?:(.*)instagram\.com|instagr\.am)(?:\/([a-zA-Z0-9\-_\\.]+))?\/(?:p|reels?)\/(?<id>[a-zA-Z0-9\-_\\.]+)(?:\/embed)?\/?$/i;

    static optionsConfig = {
        isVertical: { default: true, type: Boolean },
    };
    /**
     * Returns the embed url for a Instagram video.
     *
     * @param {string} videoId
     * @param {Object} options
     * @return {string} url
     */
    static getEmbedUrl(videoId, options = {}) {
        return `https://www.instagram.com/p/${videoId}/embed/`;
    }
    /**
     * Returns the url for the thumbnail image of the video.
     *
     * @param {string} videoId
     * @return {string} url
     */
    static getThumbnailUrl(videoId) {
        return `https://www.instagram.com/p/${videoId}/media/?size=t`;
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
        base: "https://www.instagram.com/p/B6dXGTxggTG",
        minified: "instagr.am/p/B6dXGTxggTG/",
        reel: "https://www.instagram.com/reel/B6dXGTxggTG/",
        reel2: "https://www.instagram.com/odoo.official/reel/B6dXGTxggTG/",
        reels: "https://www.instagram.com/reels/DPD1qwXDBwy/",
        embed: "https://www.instagram.com/p/B6dXGTxggTG/embed/",
    };
}
