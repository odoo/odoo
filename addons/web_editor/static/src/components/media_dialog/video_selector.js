/** @odoo-module */

import { useService } from '@web/core/utils/hooks';
import { throttle } from '@web/core/utils/timing';
import { qweb } from 'web.core';

const { Component, useState, useRef, useEffect } = owl;

class VideoOption extends Component {}
VideoOption.template = 'web_editor.VideoOption';

export class VideoSelector extends Component {
    setup() {
        this.rpc = useService('rpc');
        this.http = useService('http');

        this.PLATFORMS = {
            youtube: 'youtube',
            dailymotion: 'dailymotion',
            vimeo: 'vimeo',
            youku: 'youku',
        };

        this.OPTIONS = {
            autoplay: {
                label: this.env._t("Autoplay"),
                description: this.env._t("Videos are muted when autoplay is enabled"),
                platforms: [this.PLATFORMS.youtube, this.PLATFORMS.dailymotion, this.PLATFORMS.vimeo],
                urlParameter: 'autoplay=1',
            },
            loop: {
                label: this.env._t("Loop"),
                platforms: [this.PLATFORMS.youtube, this.PLATFORMS.vimeo],
                urlParameter: 'loop=1',
            },
            hide_controls: {
                label: this.env._t("Hide player controls"),
                platforms: [this.PLATFORMS.youtube, this.PLATFORMS.dailymotion],
                urlParameter: 'controls=0',
            },
            hide_fullscreen: {
                label: this.env._t("Hide fullscreen button"),
                platforms: [this.PLATFORMS.youtube],
                urlParameter: 'fs=0',
                isHidden: () => this.state.options.filter(option => option.id === 'hide_controls')[0].value,
            },
            hide_yt_logo: {
                label: this.env._t("Hide Youtube logo"),
                platforms: [this.PLATFORMS.youtube],
                urlParameter: 'modestbranding=1',
                isHidden: () => this.state.options.filter(option => option.id === 'hide_controls')[0].value,
            },
            hide_dm_logo: {
                label: this.env._t("Hide Dailymotion logo"),
                platforms: [this.PLATFORMS.dailymotion],
                urlParameter: 'ui-logo=0',
            },
            hide_dm_share: {
                label: this.env._t("Hide sharing button"),
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
        });
        this.urlInputRef = useRef('url-input');

        useEffect(() => {
            const initWithMedia = async () => {
                if (this.props.media) {
                    const src = this.props.media.dataset.oeExpression || this.props.media.dataset.src || (this.props.media.tagName === 'IFRAME' && this.props.media.getAttribute('src')) || '';
                    if (src) {
                        this.urlInputRef.el.value = src;
                        await this.updateVideo(src);

                        this.state.options = this.state.options.map((option) => {
                            const { urlParameter } = this.OPTIONS[option.id];
                            return { ...option, value: src.indexOf(urlParameter) >= 0 };
                        });
                    }
                }
            };

            initWithMedia();
        }, () => []);

        useEffect(() => {
            const fetchVimeoPreviews = async () => {
                await Promise.all(this.props.vimeoPreviewIds.map(async (videoId) => {
                    const { thumbnail_url: thumbnailSrc } = await this.http.get(`https://vimeo.com/api/oembed.json?url=http%3A//vimeo.com/${videoId}`);
                    this.state.vimeoPreviews.push({
                        id: videoId,
                        thumbnailSrc,
                        src: `https://player.vimeo.com/video/${videoId}`
                    });
                }));
            };

            fetchVimeoPreviews();
        }, () => []);

        this.onChangeUrl = throttle((ev) => this.updateVideo(ev.target.value), 500);
    }

    get shownOptions() {
        if (this.props.isForBgVideo) {
            return [];
        }
        return this.state.options.filter(option => !this.OPTIONS[option.id].isHidden || !this.OPTIONS[option.id].isHidden());
    }

    get errorMessage() {
        if (this.state.urlInput && !this.state.src) {
            return this.env._t("The provided url is not valid");
        }
        if (this.state.urlInput && !this.state.platform) {
            return this.env._t("The provided url does not reference any supported video");
        }
        return '';
    }

    async onChangeOption(optionId) {
        this.state.options = this.state.options.map(option => {
            if (option.id === optionId) {
                return { ...option, value: !option.value };
            }
            return option;
        });
        await this.updateVideo(this.state.urlInput);
    }

    async onClickSuggestion(src) {
        this.urlInputRef.el.value = src;
        await this.updateVideo(src);
    }

    async updateVideo(input) {
        if (!input) {
            this.state.src = '';
            this.state.urlInput = '';
            this.state.options = [];
            this.state.platform = null;
            return;
        }

        // Detect if we have an embed code rather than an URL
        const embedMatch = input.match(/(src|href)=["']?([^"']+)?/);
        if (embedMatch && embedMatch[2].length > 0 && embedMatch[2].indexOf('instagram')) {
            embedMatch[1] = embedMatch[2]; // Instagram embed code is different
        }
        const url = embedMatch ? embedMatch[1] : input;

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
        const { embed_url: src, platform } = await this.rpc('/web_editor/video_url/data', {
            video_url: url,
            ...options,
        });

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
        await this.props.selectMedia({ id: src, src }, { save: false });
        if (platform !== this.state.platform) {
            this.state.platform = platform;
            this.state.options = newOptions;
        }
        this.state.urlInput = input;
    }
}
VideoSelector.template = 'web_editor.VideoSelector';
VideoSelector.components = {
    VideoOption,
};
VideoSelector.defaultProps = {
    vimeoPreviewIds: [],
    isForBgVideo: false,
};

export const saveVideos = (selectedMedia) => {
    return selectedMedia.map(video => {
        const template = document.createElement('template');
        template.innerHTML = qweb.render('web_editor.videoWrapper', { src: video.src });
        return template.content.firstChild;
    });
};
export const videoSpecificClasses = ['media_iframe_video'];
export const videoTagNames = ['IFRAME'];
