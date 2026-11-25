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

    /**
     * Returns the url for the poster image of the video, its thumbnail unless
     * the video provider has a larger image.
     *
     * @param {string} videoId
     * @param {Object} options
     * @return {string|Promise<string>} url
     */
    static getPosterUrl(videoId, options = {}) {
        return this.getThumbnailUrl?.(videoId, options) || "";
    }

    /**
     * The message asking the player to report the playback of the video, for
     * the video providers whose player is able to.
     *
     * @type {Object|null}
     */
    static playbackSubscription = null;

    /**
     * Tells whether the message sent by the player means that it is ready to
     * receive the playback subscription. A player is always considered ready
     * once loaded.
     *
     * @param {Object} _message
     * @return {boolean}
     */
    static isReadyMessage(_message) {
        return false;
    }

    /**
     * Tells whether the message sent by the player reports that the video is
     * playing.
     *
     * @param {Object} _message
     * @return {boolean}
     */
    static isPlayingMessage(_message) {
        return false;
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
            thumbnailUrl: this.getThumbnailUrl?.(videoId, options) || "",
            options,
        };
    }

    /**
     * @param {Object} videoData @see getVideoUrlData
     * @param {Document} [document]
     * @returns {HTMLIFrameElement}
     */
    static createPlayerElement(videoData, document = window.document) {
        const iframeEl = document.createElement("iframe");
        iframeEl.setAttribute("loading", "lazy");
        iframeEl.setAttribute("frameborder", "0");
        iframeEl.setAttribute("contenteditable", "false");
        iframeEl.setAttribute("allowfullscreen", "allowfullscreen");
        iframeEl.src = videoData.embedUrl;
        return iframeEl;
    }
}
