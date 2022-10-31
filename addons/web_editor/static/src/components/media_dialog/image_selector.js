/** @odoo-module */

import { useService } from '@web/core/utils/hooks';
import { getCSSVariableValue, DEFAULT_PALETTE } from 'web_editor.utils';
import { Attachment, FileSelector, IMAGE_MIMETYPES, IMAGE_EXTENSIONS } from './file_selector';
import { KeepLast } from "@web/core/utils/concurrency";

import { useRef, useState, useEffect } from "@odoo/owl";

export class AutoResizeImage extends Attachment {
    setup() {
        super.setup();

        this.image = useRef('auto-resize-image');
        this.container = useRef('auto-resize-image-container');

        this.state = useState({
            loaded: false,
        });

        useEffect(() => {
            this.image.el.addEventListener('load', () => this.onImageLoaded());
            return this.image.el.removeEventListener('load', () => this.onImageLoaded());
        }, () => []);
    }

    async onImageLoaded() {
        if (!this.image.el) {
            // Do not fail if already removed.
            return;
        }
        if (this.props.onLoaded) {
            await this.props.onLoaded(this.image.el);
        }
        const aspectRatio = this.image.el.offsetWidth / this.image.el.offsetHeight;
        const width = aspectRatio * this.props.minRowHeight;
        this.container.el.style.flexGrow = width;
        this.container.el.style.flexBasis = `${width}px`;
        this.state.loaded = true;
    }
}
AutoResizeImage.template = 'web_editor.AutoResizeImage';

export class ImageSelector extends FileSelector {
    setup() {
        super.setup();

        this.rpc = useService('rpc');
        this.keepLastLibraryMedia = new KeepLast();

        this.state.libraryMedia = [];
        this.state.libraryResults = null;
        this.state.isFetchingLibrary = false;
        this.state.searchService = 'all';
        this.state.showOptimized = false;

        this.uploadText = this.env._t("Upload an image");
        this.urlPlaceholder = "https://www.odoo.com/logo.png";
        this.addText = this.env._t("Add URL");
        this.searchPlaceholder = this.env._t("Search an image");
        this.urlWarningTitle = this.env._t("Uploaded image's format is not supported. Try with: " + IMAGE_EXTENSIONS.join(', '));
        this.allLoadedText = this.env._t("All images have been loaded");
        this.showOptimizedOption = this.env.debug;
        this.MIN_ROW_HEIGHT = 128;

        this.fileMimetypes = IMAGE_MIMETYPES.join(',');
    }

    get canLoadMore() {
        if (this.state.searchService === 'all') {
            return super.canLoadMore || (this.state.libraryResults && this.state.libraryMedia.length < this.state.libraryResults);
        } else if (this.state.searchService === 'media-library') {
            return this.state.libraryResults && this.state.libraryMedia.length < this.state.libraryResults;
        }
        return super.canLoadMore;
    }

    get hasContent() {
        if (this.state.searchService === 'all') {
            return super.hasContent || !!this.state.libraryMedia.length;
        } else if (this.state.searchService === 'media-library') {
            return !!this.state.libraryMedia.length;
        }
        return super.hasContent;
    }

    get isFetching() {
        return super.isFetching || this.state.isFetchingLibrary;
    }

    get selectedMediaIds() {
        return this.props.selectedMedia[this.props.id].filter(media => media.mediaType === 'libraryMedia').map(({ id }) => id);
    }

    get attachmentsDomain() {
        const domain = super.attachmentsDomain;
        domain.push(['mimetype', 'in', IMAGE_MIMETYPES]);
        if (!this.props.useMediaLibrary) {
            domain.push('|', ['url', '=', false], '!', ['url', '=ilike', '/web_editor/shape/%']);
        }
        domain.push('!', ['name', '=like', '%.crop']);
        domain.push('|', ['type', '=', 'binary'], '!', ['url', '=like', '/%/static/%']);
        return domain;
    }

    async uploadFiles(files) {
        await this.uploadService.uploadFiles(files, { resModel: this.props.resModel, resId: this.props.resId, isImage: true }, (attachment) => this.onUploaded(attachment));
    }

    validateUrl(...args) {
        const { isValidUrl, path } = super.validateUrl(...args);
        const isValidFileFormat = IMAGE_EXTENSIONS.some(format => path.endsWith(format));
        return { isValidFileFormat, isValidUrl };
    }

    isInitialMedia(attachment) {
        if (this.props.media.dataset.originalSrc) {
            return this.props.media.dataset.originalSrc === attachment.image_src;
        }
        return this.props.media.getAttribute('src') === attachment.image_src;
    }

    async fetchAttachments(limit, offset) {
        const attachments = await super.fetchAttachments(limit, offset);
        // Color-substitution for dynamic SVG attachment
        const primaryColors = {};
        for (let color = 1; color <= 5; color++) {
            primaryColors[color] = getCSSVariableValue('o-color-' + color);
        }
        return attachments.map(attachment => {
            if (attachment.image_src.startsWith('/')) {
                const newURL = new URL(attachment.image_src, window.location.origin);
                // Set the main colors of dynamic SVGs to o-color-1~5
                if (attachment.image_src.startsWith('/web_editor/shape/')) {
                    newURL.searchParams.forEach((value, key) => {
                        const match = key.match(/^c([1-5])$/);
                        if (match) {
                            newURL.searchParams.set(key, primaryColors[match[1]]);
                        }
                    });
                } else {
                    // Set height so that db images load faster
                    newURL.searchParams.set('height', 2 * this.MIN_ROW_HEIGHT);
                }
                attachment.thumbnail_src = newURL.pathname + newURL.search;
            }
            if (this.selectInitialMedia() && this.isInitialMedia(attachment)) {
                this.selectAttachment(attachment);
            }
            return attachment;
        });
    }

    async fetchLibraryMedia(offset) {
        if (!this.state.needle) {
            return { media: [], results: null };
        }

        this.state.isFetchingLibrary = true;
        try {
            const response = await this.rpc(
                '/web_editor/media_library_search',
                {
                    'query': this.state.needle,
                    'offset': offset,
                },
                {
                    silent: true,
                }
            );
            this.state.isFetchingLibrary = false;
            return { media: response.media || [], results: response.results };
        } catch {
            // Either API endpoint doesn't exist or is misconfigured.
            console.error(`Couldn't reach API endpoint.`);
            this.state.isFetchingLibrary = false;
            return { media: [], results: null };
        }
    }

    async loadMore(...args) {
        await super.loadMore(...args);
        if (!this.props.useMediaLibrary) {
            return;
        }
        return this.keepLastLibraryMedia.add(this.fetchLibraryMedia(this.state.libraryMedia.length)).then(({ media }) => {
            // This is never reached if another search or loadMore occurred.
            this.state.libraryMedia.push(...media);
        });
    }

    async search(...args) {
        await super.search(...args);
        if (!this.props.useMediaLibrary) {
            return;
        }
        if (!this.state.needle) {
            this.state.searchService = 'all';
        }
        this.state.libraryMedia = [];
        this.state.libraryResults = 0;
        return this.keepLastLibraryMedia.add(this.fetchLibraryMedia(0)).then(({ media, results }) => {
            // This is never reached if a new search occurred.
            this.state.libraryMedia = media;
            this.state.libraryResults = results;
        });
    }

    async onClickAttachment(attachment) {
        this.selectAttachment(attachment);
        if (!this.props.multiSelect) {
            await this.props.save();
        }
    }

    async onClickMedia(media) {
        this.props.selectMedia({ ...media, mediaType: 'libraryMedia' });
        if (!this.props.multiSelect) {
            await this.props.save();
        }
    }

    /**
     * Utility method used by the MediaDialog component.
     */
    static async createElements(selectedMedia, { orm, rpc }) {
        // Create all media-library attachments.
        const toSave = Object.fromEntries(selectedMedia.filter(media => media.mediaType === 'libraryMedia').map(media => [
            media.id, {
                query: media.query || '',
                is_dynamic_svg: !!media.isDynamicSVG,
                dynamic_colors: media.dynamicColors,
            }
        ]));
        let savedMedia = [];
        if (Object.keys(toSave).length !== 0) {
            savedMedia = await rpc('/web_editor/save_library_media', { media: toSave });
        }
        const selected = selectedMedia.filter(media => media.mediaType === 'attachment').concat(savedMedia).map(attachment => {
            // Color-customize dynamic SVGs with the theme colors
            if (attachment.image_src && attachment.image_src.startsWith('/web_editor/shape/')) {
                const colorCustomizedURL = new URL(attachment.image_src, window.location.origin);
                colorCustomizedURL.searchParams.forEach((value, key) => {
                    const match = key.match(/^c([1-5])$/);
                    if (match) {
                        colorCustomizedURL.searchParams.set(key, getCSSVariableValue(`o-color-${match[1]}`));
                    }
                });
                attachment.image_src = colorCustomizedURL.pathname + colorCustomizedURL.search;
            }
            return attachment;
        });
        return Promise.all(selected.map(async (attachment) => {
            const imageEl = document.createElement('img');
            let src = attachment.image_src;
            if (!attachment.public) {
                let accessToken = attachment.access_token;
                if (!accessToken) {
                    [accessToken] = await orm.call(
                        'ir.attachment',
                        'generate_access_token',
                        [attachment.id],
                    );
                }
                src += `?access_token=${accessToken}`;
            }
            imageEl.src = src;
            imageEl.alt = attachment.description || '';
            return imageEl;
        }));
    }

    /**
     * This converts the colors of an svg coming from the media library to
     * the palette's ones, and make them dynamic.
     *
     * @param {HTMLElement} imgEl
     * @param {Object} media
     * @returns
     */
    async onLibraryImageLoaded(imgEl, media) {
        const mediaUrl = imgEl.src;
        try {
            const response = await fetch(mediaUrl);
            if (response.headers.get('content-type') === 'image/svg+xml') {
                const svg = await response.text();
                const dynamicColors = {};
                const combinedColorsRegex = new RegExp(Object.values(DEFAULT_PALETTE).join('|'), 'gi');
                svg.replace(combinedColorsRegex, match => {
                    const colorId = Object.keys(DEFAULT_PALETTE).find(key => DEFAULT_PALETTE[key] === match.toUpperCase());
                    const colorKey = 'c' + colorId
                    dynamicColors[colorKey] = getCSSVariableValue('o-color-' + colorId);
                });
                if (Object.keys(dynamicColors).length) {
                    media.isDynamicSVG = true;
                    media.dynamicColors = dynamicColors;
                }
            }
        } catch (_e) {
            console.error('CORS is misconfigured on the API server, image will be treated as non-dynamic.');
        }
    }
}

ImageSelector.mediaSpecificClasses = ['img', 'img-fluid', 'o_we_custom_image'];
ImageSelector.mediaSpecificStyles = [];
ImageSelector.mediaExtraClasses = [
    'rounded-circle', 'rounded', 'img-thumbnail', 'shadow',
    'w-25', 'w-50', 'w-75', 'w-100',
];
ImageSelector.tagNames = ['IMG'];
ImageSelector.attachmentsListTemplate = 'web_editor.ImagesListTemplate';
ImageSelector.components = {
    ...FileSelector.components,
    AutoResizeImage,
};
