import { _t } from "@web/core/l10n/translation";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { debounce } from "@web/core/utils/timing";

import { Component, onMounted, props, proxy, signal, t } from "@odoo/owl";
import { Switch } from "@html_editor/components/switch/switch";
import { closestElement } from "@html_editor/utils/dom_traversal";

import { Youtube } from "@html_editor/main/media/video/providers/youtube";
import { Dailymotion } from "@html_editor/main/media/video/providers/dailymotion";
import { Vimeo } from "@html_editor/main/media/video/providers/vimeo";
import { GDriveVideo } from "@html_editor/main/media/video/providers/gdrive_video";
import { Instagram } from "@html_editor/main/media/video/providers/instagram";
import { Facebook } from "@html_editor/main/media/video/providers/facebook";
import { Twitch } from "@html_editor/main/media/video/providers/twitch";
import { Loom } from "@html_editor/main/media/video/providers/loom";

export const PLATFORMS = {
    youtube: Youtube,
    instagram: Instagram,
    facebook: Facebook,
    gDrive: GDriveVideo,
    dailymotion: Dailymotion,
    vimeo: Vimeo,
    twitch: Twitch,
    loom: Loom,
};

class VideoOption extends Component {
    static template = "html_editor.VideoOption";
    static components = {
        Switch,
    };
    static props = {
        description: { type: String, optional: true },
        label: { type: String, optional: true },
        isActive: { type: Boolean, optional: true },
        value: { type: String, optional: true },
        onOptionToggled: Function,
        onTextInputed: Function,
        onTextChanged: Function,
    };

    get isInputVisible() {
        return this.props.isActive && this.props.value !== undefined;
    }
}

class VideoIframe extends Component {
    static template = "html_editor.VideoIframe";
    static props = {
        src: { type: String },
    };
}

export class VideoSelector extends Component {
    static mediaSpecificClasses = ["media_iframe_video"];
    static mediaSpecificStyles = [];
    static mediaExtraClasses = [];
    static tagNames = ["IFRAME", "DIV"];
    static template = "html_editor.VideoSelector";
    static components = {
        VideoIframe,
        VideoOption,
    };
    props = props({
        selectMedia: t.function(),
        errorMessages: t.function(),
        vimeoPreviewIds: t.array().optional([]),
        isForBgVideo: t.boolean().optional(false),
        media: t.customValidator(t.any(), (p) => p.nodeType === Node.ELEMENT_NODE).optional(),
    });

    urlInputRef = signal(null);

    setup() {
        this.http = useService("http");

        this.state = proxy({
            options: {},
            src: "",
            urlInput: "",
            platform: null,
            vimeoPreviews: [], // Background video suggestions (website)
            errorMessage: "",
        });

        this.OPTIONS = {
            autoplay: {
                label: _t("Autoplay"),
                description: _t("Videos are muted when autoplay is enabled"),
            },
            loop: {
                label: _t("Loop"),
            },
            hideControls: {
                label: _t("Hide player controls"),
            },
            hideFullscreen: {
                label: _t("Hide fullscreen button"),
                isVisible: () => !this.state.options?.hideControls?.isActive,
            },
            isVertical: {
                label: _t("Vertical"),
            },
            startFrom: {
                label: _t("Start at"),
            },
        };

        onMounted(async () => {
            const media = this.props.media;
            if (media) {
                const mediaContainer = closestElement(
                    media,
                    `.media_iframe_video, [data-embedded="video"]`
                );
                let embedUrl =
                    media.dataset.embedUrl ||
                    mediaContainer?.dataset?.embedUrl ||
                    media.dataset.src ||
                    media.dataset.oeExpression; // backward compatibility for iframe added in older odoo versions

                // Deprecated oeExpression store the url without protocol for some reason.
                if (embedUrl?.startsWith("//")) {
                    embedUrl = "https:" + embedUrl;
                }

                if (!embedUrl && media.tagName === "IFRAME") {
                    embedUrl = media.getAttribute("src");
                }
                if (embedUrl) {
                    this.state.urlInput =
                        media.dataset.baseUrl || mediaContainer?.dataset.baseUrl || embedUrl;
                    this.state.src = embedUrl;
                    this.updateOption("isVertical", mediaContainer?.dataset.isVertical);
                    this.parseOptionsFromUrl(embedUrl);
                }
            }
            await this.prepareVimeoPreviews();
        });

        useAutofocus();

        // Avoid refreshing the video data after each updateOption call,
        // since multiple options can be updated at once when parsing the url, for example.
        this.refreshVideoDataDebounced = debounce(this.refreshVideoData.bind(this), 25);
        // A longer debounce time is preferred after the time input
        // to avoid template rendering interfering with user inputting data
        this.refreshVideoDataLongDebounced = debounce(this.onTextChanged.bind(this), 2000);
        this.urlChanged = debounce(() => this.parseOptionsFromUrl(this.state.urlInput), 100);
    }

    /**
     * Return a list of options config and value for the current platform
     *
     * @returns {Array<Object>}
     */
    get visibleVideoOptions() {
        const options = [];
        if (this.props.isForBgVideo || !this.state.platform) {
            return options;
        }
        const platformOptionsConfig = PLATFORMS[this.state.platform].optionsConfig;
        for (const [id, config] of Object.entries(this.OPTIONS)) {
            const option = { id: id, ...config };
            const isVisible = config?.isVisible ? config?.isVisible() : true;
            option.isActive = !!this.state.options?.[id]?.isActive;
            if (id === "startFrom") {
                option.value = this.convertSecondsToTimestamp(this.state.options?.[id]?.value);
            }
            if (isVisible && platformOptionsConfig?.[id]) {
                options.push(option);
            }
        }
        return options;
    }

    onChangeUrl() {
        this.props.selectMedia({}); // Temporarily invalidate the selected video until the url is parsed.
        this.urlChanged();
    }

    onOptionToggled(optionId) {
        this.updateOption(optionId, !this.state.options?.[optionId]?.isActive);
    }

    updateOption(optionId, isActive) {
        this.props.selectMedia({}); // Temporarily invalidate the selected video until the url is parsed.
        const option = this.state.options?.[optionId] || {};
        this.state.options[optionId] = { ...option, isActive };
        this.refreshVideoDataDebounced();
    }

    onTextChanged(ev, optionId) {
        this.state.options[optionId].value = this.convertTimestampToSeconds(ev.target.value);
        this.refreshVideoData();
    }

    onTextInputed(ev, optionId) {
        this.props.selectMedia({}); // Temporarily invalidate the selected video when the time is updated.
        this.refreshVideoDataLongDebounced(ev, optionId);
    }

    onClickSuggestion(src) {
        this.state.urlInput = src;
        this.state.src = src;
        this.parseOptionsFromUrl(src);
    }

    /**
     * Validate the given Url and return the videoData
     *
     * @param {string} url
     */
    getVideoUrlData(url) {
        this.state.errorMessage = "";
        if (!URL.canParse(url)) {
            this.state.errorMessage = _t("The provided url is not valid");
            this.props.errorMessages(this.state.errorMessage);
            return;
        }
        // Check if the url a valid url from one of the supported platforms
        let platform = false;
        let urlMatch;
        for (const [p, pClass] of Object.entries(PLATFORMS)) {
            urlMatch = pClass.isValidVideoUrl(url);
            if (urlMatch) {
                platform = p;
                break;
            }
        }

        if (!platform) {
            this.state.errorMessage = _t("The provided url does not reference any supported video");
            this.props.errorMessages(this.state.errorMessage);
            return;
        }
        this.state.errorMessage = "";
        this.props.errorMessages(this.state.errorMessage);
        return PLATFORMS[platform].getVideoUrlData(urlMatch);
    }

    /**
     * When the url input is changed, we need to update the video preview and the options values based on the url parameters.
     *
     * @param {string} url
     */
    parseOptionsFromUrl(url) {
        const videoData = this.getVideoUrlData(url);
        if (!videoData) {
            this.state.src = "";
            this.state.options = {};
            this.state.platform = null;
            /**
             * When the url input is emptied, we need to call the `selectMedia`
             * callback function to notify the other components that the media
             * has changed.
             */
            this.props.selectMedia({});
            return;
        }

        this.state.platform = videoData.platform;

        // Update the options values based on the url parameters
        for (const option of this.visibleVideoOptions) {
            if (videoData.options?.[option.id]) {
                this.updateOption(option.id, !!videoData.options[option.id]);
                if (option.value) {
                    this.state.options[option.id].value = videoData.options[option.id];
                }
            }
        }

        this.refreshVideoData();
    }

    /**
     * When an option is updated,
     * we need to refresh the video with the new options values.
     */
    refreshVideoData() {
        if (!this.state.platform) {
            return;
        }
        const forcedOptions = {};
        const platformClass = PLATFORMS[this.state.platform];
        if (this.props.isForBgVideo) {
            forcedOptions.hideControls = true;
            forcedOptions.hideFullscreen = true;
            if (platformClass.optionsConfig.autoplay) {
                forcedOptions.autoplay = true;
            }
        } else {
            // convert current option into forced options to be encoded in the embed url.
            for (const option of this.visibleVideoOptions) {
                if (option.isActive !== undefined) {
                    if (option.value) {
                        forcedOptions[option.id] = this.convertTimestampToSeconds(option.value);
                    } else {
                        forcedOptions[option.id] = option.isActive;
                    }
                }
            }
        }

        const videoData = platformClass.getVideoUrlData(
            platformClass.isValidVideoUrl(this.state.urlInput),
            forcedOptions
        );
        this.updateVideoPreview(videoData);
    }

    async updateVideoPreview(videoData) {
        let { embedUrl, videoId, options, platform, thumbnailUrl } = videoData;
        this.state.src = embedUrl;

        options.isVertical = this.state.options?.isVertical?.isActive;

        if (thumbnailUrl instanceof Promise) {
            thumbnailUrl = await thumbnailUrl;
        }
        this.props.selectMedia({
            baseUrl: this.state.urlInput,
            platform,
            videoId,
            embedUrl,
            thumbnailUrl,
            options,
        });
    }

    /**
     * Utility method used by the MediaDialog and the videoPlugins,
     * it will create the Iframe element based on the provided selected video data
     * then return it to the caller to be inserted in the document.
     *
     * @param {Array<Object>} selectedVideos
     * @param   {string} selectedVideos.baseUrl
     * @param   {string} selectedVideos.platform
     * @param   {string} selectedVideos.videoId
     * @param   {string} selectedVideos.embedUrl
     * @param   {string} selectedVideos.thumbnailUrl
     * @param   {Object} selectedVideos.options
     * @returns {Element[]}
     */
    static createElements(selectedVideos, { document = window.document } = {}) {
        return selectedVideos.map((videoData) => {
            const div = document.createElement("div");
            div.dataset.baseUrl = videoData.baseUrl;
            div.dataset.embedUrl = videoData.embedUrl;
            div.dataset.platform = videoData.platform;
            div.dataset.videoId = videoData.videoId;
            let sizeClass = "media_iframe_video_size";
            if (videoData.options?.isVertical) {
                div.dataset.isVertical = "true";
                sizeClass = "media_iframe_video_size_for_vertical";
            }
            div.innerHTML = `
                <div class="css_editable_mode_display"></div>
                <div class="${sizeClass}" contenteditable="false"></div>
                <iframe loading="lazy" frameborder="0" contenteditable="false" allowfullscreen="allowfullscreen"></iframe>
            `;

            div.querySelector("iframe").src = videoData.embedUrl;
            return div;
        });
    }

    /**
     * Based on the config vimeo ids, prepare the vimeo previews.
     */
    async prepareVimeoPreviews() {
        await Promise.all(
            this.props.vimeoPreviewIds.map(async (videoId) => {
                try {
                    const thumbnailSrc = await Vimeo.getThumbnailUrl(videoId);
                    this.state.vimeoPreviews.push({
                        id: videoId,
                        thumbnailSrc,
                        src: Vimeo.getEmbedUrl(videoId),
                    });
                } catch (err) {
                    console.warn(`Could not get video #${videoId} from vimeo: ${err}`);
                }
            })
        );
    }

    /**
     * Utility method, to convert timestamp to seconds.
     *
     * @param {string} timestamp - The start time in HH:MM:SS format or seconds.
     * @returns {Number} - The start time in seconds.
     */
    convertTimestampToSeconds(timestamp) {
        timestamp = timestamp.trim();
        // Regular expression for HH:MM:SS format
        const timeRegex = /^(?:(\d+):)?([0-5]?\d):([0-5]?\d)$/;
        if (timeRegex.test(timestamp)) {
            return parseInt(timestamp.split(":").reduce((acc, time) => acc * 60 + +time, 0) + "");
        }
        let seconds = parseInt(timestamp);

        if (isNaN(seconds)) {
            seconds = this.parseTimeToSeconds(timestamp);
        }

        return isNaN(seconds) ? 0 : seconds;
    }
    /**
     * Utility method, to convert seconds to timestamp.
     *
     * @param {string|Number} value - The start time in seconds.
     * @returns {string} - The start time in HH:MM:SS or MM:SS format.
     */
    convertSecondsToTimestamp(value) {
        if (!value) {
            return "0:00";
        }

        let totalSeconds = value;
        if (typeof value === "string") {
            const match = value.match(/^\d+s?$/);
            if (!match) {
                return "0:00";
            }
            totalSeconds = parseInt(match[0], 10);
        }

        if (!Number.isFinite(totalSeconds) || totalSeconds <= 0) {
            return value;
        }
        const hours = Math.floor(totalSeconds / 3600);
        const minutes = Math.floor((totalSeconds % 3600) / 60);
        const seconds = totalSeconds % 60;
        const pad = (n) => String(n).padStart(2, "0");

        if (hours > 0) {
            return `${hours}:${pad(minutes)}:${pad(seconds)}`;
        }
        return `${minutes}:${pad(seconds)}`;
    }
    /**
     * Utility method, to convert 'XmYs', Xm, Ys to seconds for vimeo platform.
     *
     * @param {string} value - The start time in 'XmYs' type format.
     * @returns {string} - The start time in seconds.
     */
    parseTimeToSeconds(value) {
        const match = value?.match(/^(?:(\d+)m(\d+)s|(\d+)m|(\d+)s|(\d+))$/);
        if (!match) {
            return value;
        }
        let minutes = match[1] || match[3];
        minutes = parseInt(minutes || "0", 10);
        let seconds = match[2] || match[4] || match[5];
        seconds = parseInt(seconds || "0", 10);
        return String(minutes * 60 + seconds);
    }
}
