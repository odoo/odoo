/** @odoo-module */

import { useService } from '@web/core/utils/hooks';
import { getCSSVariableValue } from 'web_editor.utils';
import { Attachment, FileSelector, IMAGE_MIMETYPES, IMAGE_EXTENSIONS } from './file_selector';

const { useRef, useState, useEffect } = owl;

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

    onImageLoaded() {
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

        useEffect(() => {
            const initWithMedia = async () => {
                if (this.props.media && this.props.media.tagName === 'IMG') {
                    let selectedMedia = this.state.attachments.filter(attachment => {
                        if (this.props.media.dataset.originalSrc) {
                            return this.props.media.dataset.originalSrc === attachment.image_src;
                        }
                        return this.props.media.getAttribute('src') === attachment.image_src;
                    })[0];
                    if (selectedMedia) {
                        await this.selectAttachment(selectedMedia, false);
                    }
                }
            };

            initWithMedia();
        }, () => []);
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
        let domain = super.attachmentsDomain;
        domain = domain.concat([['mimetype', 'in', IMAGE_MIMETYPES]]);
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
            return attachment;
        });
    }

    async fetchLibraryMedia(offset) {
        this.state.isFetchingLibrary = true;
        if (!this.state.needle) {
            return { media: [], results: null };
        }
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
        } catch (e) {
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
        const { media } = await this.fetchLibraryMedia(this.state.libraryMedia.length);
        this.state.libraryMedia.push(...media);
    }

    async search(...args) {
        await super.search(...args);
        if (!this.props.useMediaLibrary) {
            return;
        }
        if (!this.state.needle) {
            this.state.searchService = 'all';
        }
        const { media, results } = await this.fetchLibraryMedia(0);
        this.state.libraryMedia = media;
        this.state.libraryResults = results;
    }

    async selectMedia(media) {
        await this.props.selectMedia({ ...media, mediaType: 'libraryMedia' }, { multiSelect: this.props.multiSelect });
    }
}
ImageSelector.attachmentsListTemplate = 'web_editor.ImagesListTemplate';
ImageSelector.components = {
    ...FileSelector.components,
    AutoResizeImage,
};
