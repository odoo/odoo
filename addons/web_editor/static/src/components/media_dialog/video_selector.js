/** @odoo-module */

import { useService } from '@web/core/utils/hooks';
import { Attachment, FileSelector, VIDEO_MIMETYPES } from "./file_selector";
import { Component, useState, onWillStart } from "@odoo/owl";

/* --- Constants ------------------------------------------------------------ */

const PLATFORMS = {
    YOUTUBE: "youtube",
    DAILYMOTION: "dailymotion",
    VIMEO: "vimeo",
    YOUKU: "youku",
    SELFHOSTED: "selfhosted",
};

const OPTIONS = {
    autoplay: {
        label: "Autoplay",
        description: "Videos are muted when autoplay is enabled",
        platforms: [
            PLATFORMS.YOUTUBE,
            PLATFORMS.DAILYMOTION,
            PLATFORMS.VIMEO,
            PLATFORMS.SELFHOSTED,
        ],
        urlParameter: "autoplay=1",
    },
    loop: {
        label: "Loop",
        platforms: [PLATFORMS.YOUTUBE, PLATFORMS.VIMEO, PLATFORMS.SELFHOSTED],
        urlParameter: "loop=1",
    },
    hide_controls: {
        label: "Hide player controls",
        platforms: [
            PLATFORMS.YOUTUBE,
            PLATFORMS.DAILYMOTION,
            PLATFORMS.VIMEO,
            PLATFORMS.SELFHOSTED,
        ],
        urlParameter: "controls=0",
    },
    hide_fullscreen: {
        label: "Hide fullscreen button",
        platforms: [PLATFORMS.YOUTUBE],
        urlParameter: "fs=0",
        isHidden: (options) => options.filter((option) => option.id === "hide_controls")[0].value,
    },
    hide_yt_logo: {
        label: "Hide Youtube logo",
        platforms: [PLATFORMS.YOUTUBE],
        urlParameter: "modestbranding=1",
        isHidden: (options) => options.filter((option) => option.id === "hide_controls")[0].value,
    },
    hide_dm_logo: {
        label: "Hide Dailymotion logo",
        platforms: [PLATFORMS.DAILYMOTION],
        urlParameter: "ui-logo=0",
    },
    hide_dm_share: {
        label: "Hide sharing button",
        platforms: [PLATFORMS.DAILYMOTION],
        urlParameter: "sharing-enable=0",
    },
};

/* --- Components ----------------------------------------------------------- */

class VideoOption extends Component {
    static template = "web_editor.VideoOption";
}

export class VideoAttachement extends Attachment {
    static template = "web_editor.VideoAttachement";
}

export class VideoSelector extends FileSelector {
    setup() {
        super.setup();

        this.rpc = useService("rpc");
        this.http = useService("http");
        this.orm = useService("orm");

        this.uploadText = this.env._t("Upload a video");
        this.urlPlaceholder = "URL or embed";
        this.addText = (expended) => expended ? this.env._t( "Get video") : this.env._t( "Add URL");
        this.searchPlaceholder = this.env._t("Search a video");
        this.allLoadedText = this.env._t("All video have been loaded");
        this.fileMimetypes = VIDEO_MIMETYPES.join(",");

        this.state = useState({
            options: [],
            src: "",
            urlInput: "",
            errorMessage: "",
            platform: null,
        });

        onWillStart(async () => {
            if (this.props.media) {
                const src =
                    this.props.media.dataset.oeExpression ||
                    this.props.media.dataset.src ||
                    (this.props.media.tagName === "IFRAME" &&
                        this.props.media.getAttribute("src")) ||
                    "";

                if (src) {
                    this.state.urlInput = src;
                    this.state.options = this.state.options.map((option) => {
                        const { urlParameter } = OPTIONS[option.id];
                        return { ...option, value: src.indexOf(urlParameter) >= 0 };
                    });

                    await this.updateVideo();
                }
            }
        });

        this.uploadUrl = this.uploadUrl.bind(this);
        this.validateUrl = this.validateUrl.bind(this);
    }

    get shownOptions() {
        if (this.props.isForBgVideo) {
            return [];
        }
        return this.state.options.filter(
            (option) =>
                !OPTIONS[option.id].isHidden || !OPTIONS[option.id].isHidden(this.state.options)
        );
    }

    /**
     * Keep rpc call in distinct method make it patchable by test.
     */
    async _getVideoURLData(url, options) {
        return await this.rpc("/web_editor/video_url/data", {
            video_url: url,
            ...options,
        });
    }

    async onChangeOption(optionId) {
        this.state.options = this.state.options.map((option) => {
            if (option.id === optionId) {
                return { ...option, value: !option.value };
            }
            return option;
        });
        await this.updateVideo();
        this.selectAttachment({ src: this.state.src });
    }

    extractUrlFromEmbedCode(code) {
        const embedMatch = code.match(/(src|href)=["']?([^"']+)?/);
        if (embedMatch && embedMatch[2].length > 0 && embedMatch[2].indexOf("instagram")) {
            embedMatch[1] = embedMatch[2]; // Instagram embed code is different
        }
        return embedMatch ? embedMatch[1] : code;
    }

    async updateVideo() {
        if (!this.state.urlInput) {
            this.state.src = "";
            this.state.urlInput = "";
            this.state.options = [];
            this.state.platform = null;
            this.state.errorMessage = "";
            return;
        }

        const url = this.extractUrlFromEmbedCode(this.state.urlInput);

        const options = {};
        if (this.props.isForBgVideo) {
            Object.keys(OPTIONS).forEach((key) => {
                options[key] = true;
            });
        } else {
            for (const option of this.shownOptions) {
                options[option.id] = option.value;
            }
        }

        const { embed_url: src, platform } = await this._getVideoURLData(url, options);

        if (!src) {
            this.state.errorMessage = this.env._t("The provided url is not valid");
        } else if (!platform) {
            this.state.errorMessage = this.env._t(
                "The provided url does not reference any supported video"
            );
        } else {
            this.state.errorMessage = "";
        }

        this.props.errorMessages(this.state.errorMessage);

        const newOptions = [];
        if (platform && platform !== this.state.platform) {
            Object.keys(OPTIONS).forEach((key) => {
                if (OPTIONS[key].platforms.includes(platform)) {
                    const { label, description } = OPTIONS[key];
                    newOptions.push({ id: key, label, description });
                }
            });
        }

        this.state.src = src;
        if (platform !== this.state.platform) {
            this.state.platform = platform;
            this.state.options = newOptions;
        }
    }

    get attachmentsDomain() {
        return [...super.attachmentsDomain, ["mimetype", "in", VIDEO_MIMETYPES]];
    }

    async onClickVideo(attachment) {
        let url = attachment.url;
        if (!attachment.public) {
            let access_token = attachment.access_token;
            if (!access_token) {
                [access_token] = await this.orm.call("ir.attachment", "generate_access_token", [
                    attachment.id,
                ]);
            }
            url += `?access_token=${access_token}`;
        }
        this.state.urlInput = url;
        await this.updateVideo();
        this.selectAttachment({ ...attachment, src: this.state.src });
    }

    async onUploaded(attachment) {
        attachment.platform = "selfhosted";
        this.state.attachments = [attachment, ...this.state.attachments];
        this.state.urlInput = `/watch/${attachment.id}`;
        await this.updateVideo();
        this.selectAttachment({ ...attachment, src: this.state.src });
    }

    async uploadUrl(url) {
        const { platform } = await this._getVideoURLData(url, {});

        const attachment = {
            name: url.split("/").pop(),
            url,
            mimetype: "application/vnd.odoo.video-embed",
            public: true,
            platform,
        };
        attachment.id = await this.orm.call("ir.attachment", "create", [attachment]);
        this.state.attachments = [attachment, ...this.state.attachments];
        this.state.urlInput = url;
        await this.updateVideo();
        this.selectAttachment({ ...attachment, src: this.state.src });
    }

    async validateUrl(url) {
        url = this.extractUrlFromEmbedCode(url);
        const { embed_url, platform } = await this._getVideoURLData(url, {});
        const path = url.split('?')[0];
        const isValidUrl = !!embed_url && !!platform;
        const isValidFileFormat = true;
        return { isValidUrl, isValidFileFormat, path };
    }

    /**
     * Utility method, called by the MediaDialog component.
     */
    static async createElements(selectedMedia) {
        return selectedMedia.map(media => {
            const el = document.createElement('div');
            el.dataset.oeExpression = media.src;
            el.innerHTML = `
                <div class="css_editable_mode_display"></div>
                <div class="media_iframe_video_size" contenteditable="false"></div>
                <iframe frameborder="0" contenteditable="false" allowfullscreen="allowfullscreen"></iframe>
            `;
            el.querySelector('iframe').src = media.src;
            return el;
        });
    }
}

VideoSelector.mediaSpecificClasses = ["media_iframe_video"];
VideoSelector.mediaSpecificStyles = [];
VideoSelector.mediaExtraClasses = [];
VideoSelector.tagNames = ["IFRAME", "DIV"];

VideoSelector.template = "web_editor.VideoSelector";
VideoSelector.attachmentsListTemplate = "web_editor.VideoSelector.attachments";
VideoSelector.components = {
    ...FileSelector.components,
    VideoAttachement,
    VideoOption,
};

VideoSelector.defaultProps = {
    isForBgVideo: false,
    maxUploadSizeMib: 128,
};
