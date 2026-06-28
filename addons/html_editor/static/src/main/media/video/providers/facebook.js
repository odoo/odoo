import { AbstractThirdPartyVideo } from "@html_editor/main/media/video/abstract_third_party_video";

export class Facebook extends AbstractThirdPartyVideo {
    static id = "facebook";
    static name = "Facebook";
    static urlMatcher =
        /^(?:https?:\/\/)?(?:www\.)?facebook\.com(?:\/(?:[^/]+\/)?videos\/|\/watch\/?\?v=|(?:\/username)?\/reel\/|\/plugins\/video\.php\?[^ ]*?href=.*?(?:videos|reel)%2f)(?<id>\d+)(\/|%2f)?$/i;

    /**
     * Returns the embed url for a facebook video.
     *
     * @param {string} videoId
     * @param {Object} options
     * @return {string} url
     */
    static getEmbedUrl(videoId, options = {}) {
        const encodedUrl = encodeURIComponent(
            `https://www.facebook.com/username/videos/${videoId}/`
        );
        return `https://facebook.com/plugins/video.php?href=${encodedUrl}`;
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
        base: "https://www.facebook.com/username/videos/2206239373151307/",
        watch: "facebook.com/watch/?v=2206239373151307",
        reel: "https://www.facebook.com/username/reel/2206239373151307/",
        embed: "https://www.facebook.com/plugins/video.php?href=https%3A%2F%2Fwww.facebook.com%2Fusername%2Fvideos%2F2206239373151307%2F",
    };
}
