/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { useAutofocus, useService } from '@web/core/utils/hooks';
import { debounce } from '@web/core/utils/timing';

import { Component, useState, useRef, onMounted, onWillStart } from "@odoo/owl";

class VideoOption extends Component {
    static template = "web_editor.VideoOption";
    static props = {
        description: {type: String, optional: true},
        label: {type: String, optional: true},
        onChangeOption: Function,
        value: {type: Boolean, optional: true},
    };
}

class VideoIframe extends Component {
    static template = "web_editor.VideoIframe";
    static props = {
        src: { type: String },
    };
}

export class VideoSelector extends Component {
    static mediaSpecificClasses = ["media_iframe_video"];
    static mediaSpecificStyles = [];
    static mediaExtraClasses = [];
    static tagNames = ["IFRAME", "DIV"];
    static template = "web_editor.VideoSelector";
    static components = {
        VideoIframe,
        VideoOption,
    };
    static props = {
        selectMedia: Function,
        errorMessages: Function,
        vimeoPreviewIds: {type: Array, optional: true},
        isForBgVideo: {type: Boolean, optional: true},
        media: {type: Object, optional: true},
        "*": true,
    };
    static defaultProps = {
        vimeoPreviewIds: [],
        isForBgVideo: false,
    };

    setup() {
        this.http = useService('http');

        this.PLATFORMS = {
            youtube: 'youtube',
            dailymotion: 'dailymotion',
            vimeo: 'vimeo',
            youku: 'youku',
        };

        this.OPTIONS = {
            autoplay: {
                label: _t("Autoplay"),
                description: _t("Videos are muted when autoplay is enabled"),
                platforms: [this.PLATFORMS.youtube, this.PLATFORMS.dailymotion, this.PLATFORMS.vimeo],
                urlParameter: 'autoplay=1',
            },
            loop: {
                label: _t("Loop"),
                platforms: [this.PLATFORMS.youtube, this.PLATFORMS.vimeo],
                urlParameter: 'loop=1',
            },
            hide_controls: {
                label: _t("Hide player controls"),
                platforms: [this.PLATFORMS.youtube, this.PLATFORMS.dailymotion, this.PLATFORMS.vimeo],
                urlParameter: 'controls=0',
            },
            hide_fullscreen: {
                label: _t("Hide fullscreen button"),
                platforms: [this.PLATFORMS.youtube],
                urlParameter: 'fs=0',
                isHidden: () => this.state.options.filter(option => option.id === 'hide_controls')[0].value,
            },
            hide_dm_logo: {
                label: _t("Hide Dailymotion logo"),
                platforms: [this.PLATFORMS.dailymotion],
                urlParameter: 'ui-logo=0',
            },
            hide_dm_share: {
                label: _t("Hide sharing button"),
                platforms: [this.PLATFORMS.dailymotion],
                urlParameter: 'sharing-enable=0',
            },
        };

        this.state = useState({
            options: [],
            src: '',
            urlInput: '',
            platform: null,
            vimeoPreviews: [],
            errorMessage: '',
        });
        this.urlInputRef = useRef('url-input');

        onWillStart(async () => {
            if (this.props.media) {
                const src = this.props.media.dataset.oeExpression || this.props.media.dataset.src || (this.props.media.tagName === 'IFRAME' && this.props.media.getAttribute('src')) || '';
                if (src) {
                    this.state.urlInput = src;
                    await this.updateVideo();

                    this.state.options = this.state.options.map((option) => {
                        const { urlParameter } = this.OPTIONS[option.id];
                        return { ...option, value: src.indexOf(urlParameter) >= 0 };
                    });
                }
            }
        });

        onMounted(async () => {
            await Promise.all(this.props.vimeoPreviewIds.map(async (videoId) => {
                const { thumbnail_url: thumbnailSrc } = await this.http.get(`https://vimeo.com/api/oembed.json?url=http%3A//vimeo.com/${encodeURIComponent(videoId)}`);
                this.state.vimeoPreviews.push({
                    id: videoId,
                    thumbnailSrc,
                    src: `https://player.vimeo.com/video/${encodeURIComponent(videoId)}`
                });
            }));
        });

        useAutofocus();

        this.onChangeUrl = debounce((ev) => this.updateVideo(ev.target.value), 500);
    }

    get shownOptions() {
        if (this.props.isForBgVideo) {
            return [];
        }
        return this.state.options.filter(option => !this.OPTIONS[option.id].isHidden || !this.OPTIONS[option.id].isHidden());
    }

    async onChangeOption(optionId) {
        this.state.options = this.state.options.map(option => {
            if (option.id === optionId) {
                return { ...option, value: !option.value };
            }
            return option;
        });
        await this.updateVideo();
    }

    async onClickSuggestion(src) {
        this.state.urlInput = src;
        await this.updateVideo();
    }

    async updateVideo() {
        if (!this.state.urlInput) {
            this.state.src = '';
            this.state.urlInput = '';
            this.state.options = [];
            this.state.platform = null;
            this.state.errorMessage = '';
            /**
             * When the url input is emptied, we need to call the `selectMedia`
             * callback function to notify the other components that the media
             * has changed.
             */
            this.props.selectMedia({});
            return;
        }

        // Detect if we have an embed code rather than an URL
        const embedMatch = this.state.urlInput.match(/(src|href)=["']?([^"']+)?/);
        if (embedMatch && embedMatch[2].length > 0 && embedMatch[2].indexOf('instagram')) {
            embedMatch[1] = embedMatch[2]; // Instagram embed code is different
        }
        const url = embedMatch ? embedMatch[1] : this.state.urlInput;

        const options = {};
        if (this.props.isForBgVideo) {
            Object.keys(this.OPTIONS).forEach(key => {
                options[key] = true;
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
            platform
        } = await this._getVideoURLData(url, options);

        if (!src) {
            this.state.errorMessage = _t("The provided url is not valid");
        } else if (!platform) {
            this.state.errorMessage =
                _t("The provided url does not reference any supported video");
        } else {
            this.state.errorMessage = '';
        }
        this.props.errorMessages(this.state.errorMessage);

        const newOptions = [];
        if (platform && platform !== this.state.platform) {
            Object.keys(this.OPTIONS).forEach(key => {
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
            params
        });
        if (platform !== this.state.platform) {
            this.state.platform = platform;
            this.state.options = newOptions;
        }
    }

    /**
     * Keep rpc call in distinct method make it patchable by test.
     */
    async _getVideoURLData(url, options) {
        return await rpc('/web_editor/video_url/data', {
            video_url: url,
            ...options,
        });
    }

    /**
     * Utility method, called by the MediaDialog component.
     */
    static createElements(selectedMedia) {
        return selectedMedia.map(video => {
            const div = document.createElement('div');
            div.dataset.oeExpression = video.src;
            div.innerHTML = `
                <div class="css_editable_mode_display"></div>
                <div class="media_iframe_video_size" contenteditable="false"></div>
                <iframe loading="lazy" frameborder="0" contenteditable="false" allowfullscreen="allowfullscreen"></iframe>
            `;
            div.querySelector('iframe').src = video.src;
            return div;
        });
    }
}
