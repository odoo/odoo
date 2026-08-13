/**
 * A video served as a plain video file, referenced by a url pointing at the
 * file itself.
 */
export class VideoFile {
    static id = "video_file";
    static name = "Video file";

    static optionsConfig = {
        autoplay: { default: false, type: Boolean },
        muted: { default: false, type: Boolean },
        loop: { default: false, type: Boolean },
        hideControls: { default: false, type: Boolean },
        isVertical: { default: false, type: Boolean },
        startFrom: { default: 0, type: Number },
    };

    /**
     * @param {string} url
     * @returns {URL|boolean} the parsed url || false
     */
    static parseUrl(url) {
        url = (url || "").trim();
        if (!url) {
            return false;
        }
        let parsedUrl;
        try {
            parsedUrl = new URL(url);
        } catch {
            return false;
        }
        return ["http:", "https:"].includes(parsedUrl.protocol) ? parsedUrl : false;
    }

    /**
     * @see AbstractThirdPartyVideo.isValidVideoUrl
     *
     * @param {string} url
     * @returns {Promise<array|boolean>} a match of the same shape as the other
     *      providers return || false
     */
    static async isValidVideoUrl(url) {
        if (!this.parseUrl(url)) {
            return false;
        }
        const isVideo = await new Promise((resolve) => {
            const videoEl = document.createElement("video");
            const conclude = (isVideo) => {
                clearTimeout(timeoutId);
                // Drop whatever is still being downloaded.
                videoEl.removeAttribute("src");
                videoEl.load();
                resolve(isVideo);
            };
            const timeoutId = setTimeout(() => conclude(false), 8000);
            videoEl.onloadedmetadata = () => conclude(true);
            videoEl.onerror = () => conclude(false);
            videoEl.preload = "metadata";
            videoEl.muted = true;
            videoEl.src = url;
        });
        return isVideo ? [url.trim()] : false;
    }

    /**
     * @see AbstractThirdPartyVideo.getVideoUrlData
     *
     * @param {array} urlMatch The result of {@link isValidVideoUrl}
     * @param {Object} [forcedOptions={}]
     */
    static getVideoUrlData(urlMatch, forcedOptions = {}) {
        const url = urlMatch[0].trim();
        // The start time is the only option stored in the url, as a media
        // fragment. Split it out so that the base url stays stable when the
        // option is edited.
        const [baseUrl, fragment = ""] = url.split(/#(.*)/);
        const startFrom = parseInt(fragment.match(/^t=(\d+)/)?.[1] || 0, 10);

        const options = {
            ...Object.fromEntries(
                Object.entries(this.optionsConfig).map(([name, config]) => [name, config.default])
            ),
            startFrom,
            ...forcedOptions,
        };
        // always mute video when autoplay is enabled
        if (options.autoplay) {
            options.muted = true;
        }

        return {
            baseUrl,
            platform: this.id,
            videoId: "",
            embedUrl: this.getEmbedUrl(baseUrl, options),
            thumbnailUrl: "",
            options,
        };
    }

    /**
     * @see AbstractThirdPartyVideo.getEmbedUrl
     *
     * @param {string} url
     * @param {Object} options
     * @return {string} url
     */
    static getEmbedUrl(url, options = {}) {
        const startFrom = parseInt(options.startFrom, 10);
        return startFrom > 0 ? `${url}#t=${startFrom}` : url;
    }

    /**
     * @see AbstractThirdPartyVideo.createPlayerElement
     *
     * @param {Object} videoData @see getVideoUrlData
     * @param {Document} [document]
     * @returns {HTMLVideoElement}
     */
    static createPlayerElement(videoData, document = window.document) {
        const { embedUrl, options = {} } = videoData;
        const videoEl = document.createElement("video");
        videoEl.setAttribute("src", embedUrl);
        // Without it, mobile browsers play the video fullscreen.
        videoEl.setAttribute("playsinline", "");
        videoEl.toggleAttribute("controls", !options.hideControls);
        videoEl.toggleAttribute("loop", !!options.loop);
        videoEl.toggleAttribute("autoplay", !!options.autoplay);
        videoEl.toggleAttribute("muted", !!options.muted);
        // The attribute alone only mutes an element created by the html parser,
        // which is the case of the saved video but not of this one.
        videoEl.muted = !!options.muted;
        if (!options.autoplay) {
            // do not download the whole file until the visitor plays it.
            videoEl.setAttribute("preload", "metadata");
        }
        videoEl.setAttribute("contenteditable", "false");
        return videoEl;
    }

    /**
     * Read back the options of an already inserted video.
     *
     * @param {HTMLVideoElement} videoEl
     * @returns {Object}
     */
    static getOptionsFromElement(videoEl) {
        return {
            autoplay: videoEl.hasAttribute("autoplay"),
            loop: videoEl.hasAttribute("loop"),
            hideControls: !videoEl.hasAttribute("controls"),
        };
    }
}
