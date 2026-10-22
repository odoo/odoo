import { AbstractThirdPartyVideo } from "@html_editor/main/media/video/abstract_third_party_video";
import { encodeOptionsToParams } from "@html_editor/main/media/video/utils";

export class Dailymotion extends AbstractThirdPartyVideo {
    static id = "dailymotion";
    static name = "Dailymotion";
    static urlMatcher =
        /^(https?:\/\/)(www\.)?(dailymotion\.com\/(embed\/video\/|embed\/|video\/|hub\/.*#video=)|geo\.dailymotion\.com\/player\.html\?video=|dai\.ly\/)(?<id>[A-Za-z0-9]{6,7})(?:[-_][-_a-z]*)?(?:[?&=](?:[0-9a-z]+))*$/i;

    static optionsConfig = {
        startFrom: { default: 0, type: Number, params: ["startTime"] },
    };
    /**
     * Returns the embed url for a dailymotion video.
     *
     * @param {string} videoId
     * @param {Object} options
     * @return {string} url
     */
    static getEmbedUrl(videoId, options = {}) {
        const params = encodeOptionsToParams(options, Dailymotion.optionsConfig);
        return `https://geo.dailymotion.com/player.html?video=${videoId}${
            params ? "&" + params : ""
        }`;
    }
    /**
     * Returns the url for the thumbnail image of the video.
     *
     * @param {string} videoId
     * @return {string} url
     */
    static getThumbnailUrl(videoId) {
        return `https://www.dailymotion.com/thumbnail/video/${videoId}`;
    }
}
