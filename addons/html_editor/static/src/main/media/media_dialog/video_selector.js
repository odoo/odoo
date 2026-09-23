/** @odoo-module native */
import { Switch } from "@html_editor/components/switch/switch";
import { Component, onMounted, status, useRef, useState } from "@odoo/owl";
import { rpc } from "@web/core/network";
import { _t } from "@web/core/translation";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { debounce } from "@web/core/utils/timing";

class VideoOption extends Component {
    static template = "html_editor.VideoOption";
    static components = {
        Switch,
    };
    static props = {
        description: { type: String, optional: true },
        label: { type: String, optional: true },
        onChangeOption: Function,
        onChangeStartAt: Function,
        value: { type: String, optional: true },
        name: { type: String, optional: true },
    };

    get showStartAtInput() {
        return this.props.name === "start_from";
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
    static props = {
        selectMedia: Function,
        errorMessages: Function,
        vimeoPreviewIds: { type: Array, optional: true },
        isForBgVideo: { type: Boolean, optional: true },
        media: { validate: (p) => p.nodeType === Node.ELEMENT_NODE, optional: true },
        "*": true,
    };
    static defaultProps = {
        vimeoPreviewIds: [],
        isForBgVideo: false,
    };

    setup() {
        this.http = useService("http");

        this.state = useState({
            options: [],
            src: "",
            urlInput: "",
            platform: null,
            vimeoPreviews: [],
            errorMessage: "",
        });

        this.PLATFORMS = {
            youtube: "youtube",
            dailymotion: "dailymotion",
            vimeo: "vimeo",
        };

        this.platformParams = {
            youtube: "start",
            dailymotion: "startTime",
            vimeo: "#t=",
        };

        this.OPTIONS = {
            autoplay: {
                label: _t("Autoplay"),
                description: _t("Videos are muted when autoplay is enabled"),
                platforms: [this.PLATFORMS.youtube, this.PLATFORMS.vimeo],
                urlParameter: () => "autoplay=1",
            },
            loop: {
                label: _t("Loop"),
                platforms: [this.PLATFORMS.youtube, this.PLATFORMS.vimeo],
                urlParameter: () => "loop=1",
            },
            hide_controls: {
                label: _t("Hide player controls"),
                platforms: [this.PLATFORMS.youtube, this.PLATFORMS.vimeo],
                urlParameter: () => "controls=0",
            },
            hide_fullscreen: {
                label: _t("Hide fullscreen button"),
                platforms: [this.PLATFORMS.youtube],
                urlParameter: () => "fs=0",
                isHidden: () =>
                    this.state.options.filter(
                        (option) => option.id === "hide_controls",
                    )[0].value,
            },
            start_from: {
                label: _t("Start at"),
                platforms: [
                    this.PLATFORMS.youtube,
                    this.PLATFORMS.vimeo,
                    this.PLATFORMS.dailymotion,
                ],
                urlParameter: () => this.platformParams[this.state.platform],
            },
        };
        this.urlInputRef = useRef("url-input");

        onMounted(async () => {
            if (this.props.media) {
                const src =
                    this.props.media.dataset.oeExpression ||
                    this.props.media.dataset.src ||
                    (this.props.media.tagName === "IFRAME" &&
                        this.props.media.getAttribute("src")) ||
                    "";
                if (src) {
                    this.state.urlInput = src;
                    if (!src.startsWith("https:") && !src.startsWith("http:")) {
                        this.state.urlInput = "https:" + this.state.urlInput;
                    }
                    await this.syncOptionsWithUrl();
                    if (status(this) === "destroyed") {
                        return;
                    }
                }
            }
            await this.prepareVimeoPreviews();
        });

        useAutofocus();

        this.onChangeUrl = debounce(() => this.syncOptionsWithUrl(), 500);

        this.onChangeStartAt = debounce(async (ev, optionId) => {
            const start_from = this.convertTimestampToSeconds(ev.target.value);
            this.state.options = this.state.options.map((option) => {
                if (option.id === optionId) {
                    return {
                        ...option,
                        value: start_from === "0" ? "00:00" : start_from,
                    };
                }
                return option;
            });
            await this.updateVideo();
            this.state.urlInput = "https:" + this.state.src;
        }, 1000);
    }

    get shownOptions() {
        if (this.props.isForBgVideo) {
            return [];
        }
        return this.state.options.filter(
            (option) =>
                !this.OPTIONS[option.id].isHidden ||
                !this.OPTIONS[option.id].isHidden(),
        );
    }

    optionValue(option) {
        if (option.id === "start_from" && option.value !== "00:00") {
            return this.convertSecondsToTimestamp(option.value);
        }
        return option.value;
    }

    async onChangeOption(optionId) {
        this.state.options = this.state.options.map((option) => {
            if (option.id === optionId) {
                return { ...option, value: !option.value && "00:00" };
            }
            return option;
        });
        await this.updateVideo();
        this.state.urlInput = "https:" + this.state.src;
    }

    async onClickSuggestion(src) {
        this.state.urlInput = src;
        await this.updateVideo();
    }

    async updateVideo() {
        if (!this.state.urlInput) {
            this.state.src = "";
            this.state.urlInput = "";
            this.state.options = [];
            this.state.platform = null;
            this.state.errorMessage = "";
            this.props.selectMedia({});
            return;
        }

        const embedMatch = this.state.urlInput.match(/(src|href)=["']?([^"']+)?/);
        if (
            embedMatch &&
            embedMatch[2].length > 0 &&
            !embedMatch[2].includes("instagram")
        ) {
            embedMatch[1] = embedMatch[2];
        }
        const url = embedMatch ? embedMatch[1] : this.state.urlInput;

        const options = {};
        if (this.props.isForBgVideo && URL.canParse(url)) {
            const parsedUrl = new URL(url);
            const urlParams = parsedUrl.searchParams;
            const startFrom =
                urlParams.get("start") ||
                urlParams.get("startTime") ||
                urlParams.get("t");
            Object.keys(this.OPTIONS).forEach((key) => {
                options[key] = key === "start_from" ? startFrom : true;
            });
        } else {
            for (const option of this.shownOptions) {
                options[option.id] = option.value;
            }
        }

        const {
            embed_url: src,
            video_id: videoId,
            params,
            platform,
        } = await this._getVideoURLData(url, options);

        if (!src) {
            this.state.errorMessage = _t("The provided url is not valid");
        } else if (!platform) {
            this.state.errorMessage = _t(
                "The provided url does not reference any supported video",
            );
        } else {
            this.state.errorMessage = "";
        }
        this.props.errorMessages(this.state.errorMessage);

        const newOptions = [];
        if (platform && platform !== this.state.platform) {
            Object.keys(this.OPTIONS).forEach((key) => {
                if (this.OPTIONS[key].platforms.includes(platform)) {
                    const { label, description } = this.OPTIONS[key];
                    newOptions.push({ id: key, label, description });
                }
            });
        }

        this.state.src = src;
        this.props.selectMedia({
            id: src,
            src,
            platform,
            videoId,
            params,
        });
        if (platform !== this.state.platform) {
            this.state.platform = platform;
            this.state.options = newOptions;
        }
    }

    async _getVideoURLData(url, options) {
        return await rpc("/html_editor/video_url/data", {
            video_url: url,
            ...options,
        });
    }

    static createElements(selectedMedia) {
        return selectedMedia.map((video) => {
            const div = document.createElement("div");
            div.dataset.oeExpression = video.src;
            div.innerHTML =
                '<div class="css_editable_mode_display"></div>' +
                '<div class="media_iframe_video_size" contenteditable="false"></div>' +
                '<iframe frameborder="0" contenteditable="false" allowfullscreen="allowfullscreen"></iframe>';

            div.querySelector("iframe").src = video.src;
            return div;
        });
    }

    async prepareVimeoPreviews() {
        await Promise.all(
            this.props.vimeoPreviewIds.map(async (videoId) => {
                try {
                    const { thumbnail_url: thumbnailSrc } = await this.http.get(
                        `https://vimeo.com/api/oembed.json?url=http%3A//vimeo.com/${encodeURIComponent(
                            videoId,
                        )}`,
                    );
                    this.state.vimeoPreviews.push({
                        id: videoId,
                        thumbnailSrc,
                        src: `https://player.vimeo.com/video/${encodeURIComponent(videoId)}`,
                    });
                } catch (err) {
                    console.warn(`Could not get video #${videoId} from vimeo: ${err}`);
                }
            }),
        );
    }

    async syncOptionsWithUrl() {
        await this.updateVideo();
        if (!URL.canParse(this.state.urlInput)) {
            return;
        }
        const parsedUrl = new URL(this.state.urlInput);
        const urlParams = parsedUrl.searchParams;
        this.state.options = this.state.options.map((option) => {
            const urlParameter = this.OPTIONS[option.id].urlParameter();
            let value;

            switch (urlParameter) {
                case "#t=":
                    value = this.parseTimeToSeconds(
                        this.state.urlInput.split("#t=")[1],
                    );
                    break;
                case "start":
                    value = urlParams.get("start") || urlParams.get("t");
                    break;
                case "startTime":
                    value = urlParams.get("startTime") || urlParams.get("start");
                    break;
                default:
                    value = this.state.urlInput.includes(urlParameter);
            }
            if (option.id === "start_from" && value === "0") {
                return { ...option, value: "00:00" };
            }
            return { ...option, value: value || "" };
        });
        await this.updateVideo();
    }

    /**
     * @param {string} timestamp
     * @returns {string}
     */
    convertTimestampToSeconds(timestamp) {
        timestamp = timestamp.trim();
        const timeRegex = /^(?:(\d+):)?([0-5]?\d):([0-5]?\d)$/;
        if (timeRegex.test(timestamp)) {
            return timestamp.split(":").reduce((acc, time) => acc * 60 + +time, 0) + "";
        }
        if (isNaN(timestamp)) {
            return "0";
        }
        return timestamp;
    }
    /**
     * @param {string} value
     * @returns {string}
     */
    convertSecondsToTimestamp(value) {
        if (!value) {
            return "";
        }
        const match = value.match(/^\d+s?$/);
        if (!match) {
            return "";
        }

        const totalSeconds = parseInt(match[0], 10);
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
     * @param {string} value
     * @returns {string}
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
