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
}
