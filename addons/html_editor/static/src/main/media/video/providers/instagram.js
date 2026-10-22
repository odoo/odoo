import { AbstractThirdPartyVideo } from "@html_editor/main/media/video/abstract_third_party_video";

export class Instagram extends AbstractThirdPartyVideo {
    static id = "instagram";
    static name = "Instagram";

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
}
