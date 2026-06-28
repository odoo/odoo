import { getUrlOptions } from "@html_editor/main/media/video/utils";

/**
 * @abstract
 * @class AbstractThirdPartyVideo
 * @classdesc Abstract class for third party video providers.
 */
export class AbstractThirdPartyVideo {
    // ------------------------------------------------------
    // Methods and properties to be implemented by subclasses.
    // ------------------------------------------------------

    /**
     * The unique id of the video provider.
     * @type {string}
     */
    static id = "";

    /**
     * The display name of the video provider, used in the UI.
     * @type {string}
     */
    static name = "";

    /**
     * A regex used to match and extract the video id from the url,
     * it should have a named group "id" that will be used to extract the video id.
     * The regex MUST match all valid urls of the video provider.
     * @see {@link isValidVideoUrl}
     *
     * @type {RegExp}
     */
    static urlMatcher = /$/i;

    /**
     * List the options that can be extracted from the url and passed to the embed url.
     * @see {@link encodeOptionsToParams}
     * @see {@link getUrlOptions}
     *
     * example:
     *   ```
     *   static optionsConfig = {
     *         startFrom: { default: 0, type: Number, params: ["time"] },
     *         autoplay: { default: true, type: Boolean, params: ["autoplay"] },
     *         ...
     *   };
     *   ```
     *
     * @type {{}}
     */
    static optionsConfig = {};

    /**
     * Returns the embed url for the implemeted video provider.
     *
     * @param {string} videoId
     * @param {Object} options
     * @return {string} url
     */
    static getEmbedUrl(videoId, options = {}) {
        return "";
    }

    // ------------------------------------------------------
    // Methods common to all video providers are implemented here.
    // ------------------------------------------------------

    /**
     * Check if the url is a valid video url.
     *
     * @param {String} url
     * @returns {array|boolean} a regex match || false
     */
    static isValidVideoUrl(url) {
        url = url.trim();
        if (!/^https?:\/\//.test(url)) {
            url = "https://" + url;
        }
        if (!URL.canParse(url)) {
            return false;
        }
        return this.urlMatcher.exec(url) || false;
    }

    /**
     * Returns the video data extracted from the provided url.
     *
     * @param {array} urlMatch The result of the regex match of the url
     * @param {Object} [forcedOptions={}]
     */
    static getVideoUrlData(urlMatch, forcedOptions = {}) {
        const baseUrl = new URL(urlMatch[0]);
        const videoId = urlMatch.groups.id;
        const options = {
            ...getUrlOptions(baseUrl, this.optionsConfig || {}),
            ...(this?.getCustomUrlOptions?.(baseUrl) || {}),
            ...forcedOptions,
        };
        // always mute video when autoplay is enabled
        if (options.autoplay) {
            options.muted = true;
        }

        return {
            baseUrl: urlMatch[0],
            platform: this.id,
            videoId,
            embedUrl: this.getEmbedUrl(videoId, options),
            // thumbnailUrl can be a promise in some cases (see vimeo)
            thumbnailUrl: this.getThumbnailUrl?.(videoId) || "",
            options,
        };
    }
}
