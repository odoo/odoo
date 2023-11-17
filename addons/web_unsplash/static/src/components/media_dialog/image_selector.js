/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { KeepLast } from "@web/core/utils/concurrency";
import { MediaDialog, TABS } from '@web_editor/components/media_dialog/media_dialog';
import { ImageSelector } from '@web_editor/components/media_dialog/image_selector';
import { useService } from '@web/core/utils/hooks';
import { uploadService, AUTOCLOSE_DELAY } from '@web_editor/components/upload_progress_toast/upload_service';

import { useState, Component } from "@odoo/owl";

class UnsplashCredentials extends Component {
    setup() {
        this.state = useState({
            key: '',
            appId: '',
            hasKeyError: this.props.hasCredentialsError,
            hasAppIdError: this.props.hasCredentialsError,
        });
    }

    submitCredentials() {
        if (this.state.key === '') {
            this.state.hasKeyError = true;
        } else if (this.state.appId === '') {
            this.state.hasAppIdError = true;
        } else {
            this.props.submitCredentials(this.state.key, this.state.appId);
        }
    }
}
UnsplashCredentials.template = 'web_unsplash.UnsplashCredentials';

export class UnsplashError extends Component {}
UnsplashError.template = 'web_unsplash.UnsplashError';
UnsplashError.components = {
    UnsplashCredentials,
};

patch(ImageSelector.prototype, {
    setup() {
        super.setup();
        this.unsplash = useService('unsplash');
        this.keepLastUnsplash = new KeepLast();

        this.state.unsplashRecords = [];
        this.state.isFetchingUnsplash = false;
        this.state.isMaxed = false;
        this.state.unsplashError = null;
        this.state.useUnsplash = true;
        this.NUMBER_OF_RECORDS_TO_DISPLAY = 30;

        this.errorMessages = {
            'key_not_found': {
                title: _t("Setup Unsplash to access royalty free photos."),
                subtitle: "",
            },
            401: {
                title: _t("Unauthorized Key"),
                subtitle: _t("Please check your Unsplash access key and application ID."),
            },
            403: {
                title: _t("Search is temporarily unavailable"),
                subtitle: _t("The max number of searches is exceeded. Please retry in an hour or extend to a better account."),
            },
        };
    },

    get canLoadMore() {
        if (this.state.searchService === 'all') {
            return super.canLoadMore || this.state.needle && !this.state.isMaxed && !this.state.unsplashError;
        } else if (this.state.searchService === 'unsplash') {
            return this.state.needle && !this.state.isMaxed && !this.state.unsplashError;
        }
        return super.canLoadMore;
    },

    get hasContent() {
        if (this.state.searchService === 'all') {
            return super.hasContent || !!this.state.unsplashRecords.length;
        } else if (this.state.searchService === 'unsplash') {
            return !!this.state.unsplashRecords.length;
        }
        return super.hasContent;
    },

    get errorTitle() {
        if (this.errorMessages[this.state.unsplashError]) {
            return this.errorMessages[this.state.unsplashError].title;
        }
        return _t("Something went wrong");
    },

    get errorSubtitle() {
        if (this.errorMessages[this.state.unsplashError]) {
            return this.errorMessages[this.state.unsplashError].subtitle;
        }
        return _t("Please check your internet connection or contact administrator.");
    },

    get selectedRecordIds() {
        return this.props.selectedMedia[this.props.id].filter(media => media.mediaType === 'unsplashRecord').map(({ id }) => id);
    },

    get isFetching() {
        return super.isFetching || this.state.isFetchingUnsplash;
    },

    get combinedRecords() {
        /**
         * Creates an array with alternating elements from two arrays.
         *
         * @param {Array} a
         * @param {Array} b
         * @returns {Array} alternating elements from a and b, starting with
         *     an element of a
         */
        function alternate(a, b) {
            return [
                a.map((v, i) => i < b.length ? [v, b[i]] : v),
                b.slice(a.length),
            ].flat(2);
        }
        return alternate(this.state.unsplashRecords, this.state.libraryMedia);
    },

    get allAttachments() {
        return [...super.allAttachments, ...this.state.unsplashRecords];
    },

    // It seems that setters are mandatory when patching a component that
    // extends another component.
    set canLoadMore(_) {},
    set hasContent(_) {},
    set isFetching(_) {},
    set selectedMediaIds(_) {},
    set attachmentsDomain(_) {},
    set errorTitle(_) {},
    set errorSubtitle(_) {},
    set selectedRecordIds(_) {},

    async fetchUnsplashRecords(offset) {
        if (!this.state.needle) {
            return { records: [], isMaxed: false };
        }
        this.state.isFetchingUnsplash = true;
        try {
            const { isMaxed, images } = await this.unsplash.getImages(this.state.needle, offset, this.NUMBER_OF_RECORDS_TO_DISPLAY, this.props.orientation);
            this.state.isFetchingUnsplash = false;
            this.state.unsplashError = false;
            const records = images.map(record => {
                const url = new URL(record.urls.regular);
                // In small windows, row height could get quite a bit larger than the min, so we keep some leeway.
                url.searchParams.set('h', 2 * this.MIN_ROW_HEIGHT);
                url.searchParams.delete('w');
                return Object.assign({}, record, {
                    url: url.toString(),
                    mediaType: 'unsplashRecord',
                });
            });
            return { isMaxed, records };
        } catch (e) {
            this.state.isFetchingUnsplash = false;
            if (e === 'no_access') {
                this.state.useUnsplash = false;
            } else {
                this.state.unsplashError = e;
            }
            return { records: [], isMaxed: true };
        }
    },

    async loadMore(...args) {
        await super.loadMore(...args);
        return this.keepLastUnsplash.add(this.fetchUnsplashRecords(this.state.unsplashRecords.length)).then(({ records, isMaxed }) => {
            // This is never reached if another search or loadMore occurred.
            this.state.unsplashRecords.push(...records);
            this.state.isMaxed = isMaxed;
        });
    },

    async search(...args) {
        await super.search(...args);
        await this.searchUnsplash();
    },

    async searchUnsplash() {
        if (!this.state.needle) {
            this.state.unsplashError = false;
            this.state.unsplashRecords = [];
            this.state.isMaxed = false;
        }
        return this.keepLastUnsplash.add(this.fetchUnsplashRecords(0)).then(({ records, isMaxed }) => {
            // This is never reached if a new search occurred.
            this.state.unsplashRecords = records;
            this.state.isMaxed = isMaxed;
        });
    },

    async onClickRecord(media) {
        this.props.selectMedia({ ...media, mediaType: 'unsplashRecord', query: this.state.needle });
        if (!this.props.multiSelect) {
            await this.props.save();
        }
    },

    async submitCredentials(key, appId) {
        this.state.unsplashError = null;
        await this.rpc('/web_unsplash/save_unsplash', { key, appId });
        await this.searchUnsplash();
    },
});
ImageSelector.components = {
    ...ImageSelector.components,
    UnsplashError,
};

patch(MediaDialog.prototype, {
    setup() {
        super.setup();

        this.uploadService = useService('upload');
    },

    async save() {
        const selectedImages = this.selectedMedia[TABS.IMAGES.id];
        if (selectedImages) {
            const unsplashRecords = selectedImages.filter(media => media.mediaType === 'unsplashRecord');
            if (unsplashRecords.length) {
                await this.uploadService.uploadUnsplashRecords(unsplashRecords, { resModel: this.props.resModel, resId: this.props.resId }, (attachments) => {
                    this.selectedMedia[TABS.IMAGES.id] = this.selectedMedia[TABS.IMAGES.id].filter(media => media.mediaType !== 'unsplashRecord');
                    this.selectedMedia[TABS.IMAGES.id] = this.selectedMedia[TABS.IMAGES.id].concat(attachments.map(attachment => ({...attachment, mediaType: 'attachment'})));
                });
            }
        }
        return super.save(...arguments);
    },
});

patch(uploadService, {
    start(env, { rpc }) {
        const service = super.start(...arguments);
        return {
            ...service,
            async uploadUnsplashRecords(records, { resModel, resId }, onUploaded) {
                service.incrementId();
                const file = service.addFile({
                    id: service.fileId,
                    name: records.length > 1 ?
                    _t("Uploading %s '%s' images.", records.length, records[0].query) :
                    _t("Uploading '%s' image.", records[0].query),
                });

                try {
                    const urls = {};
                    for (const record of records) {
                        const _1920Url = new URL(record.urls.regular);
                        _1920Url.searchParams.set('w', '1920');
                        urls[record.id] = {
                            url: _1920Url.href,
                            download_url: record.links.download_location,
                            description: record.alt_description,
                        };
                    }

                    const xhr = new XMLHttpRequest();
                    xhr.upload.addEventListener('progress', ev => {
                        const rpcComplete = ev.loaded / ev.total * 100;
                        file.progress = rpcComplete;
                    });
                    xhr.upload.addEventListener('load', function () {
                        // Don't show yet success as backend code only starts now
                        file.progress = 100;
                    });
                    const attachments = await rpc('/web_unsplash/attachment/add', {
                        'res_id': resId,
                        'res_model': resModel,
                        'unsplashurls': urls,
                        'query': records[0].query,
                    }, {xhr});

                    if (attachments.error) {
                        file.hasError = true;
                        file.errorMessage = attachments.error;
                    } else {
                        file.uploaded = true;
                        await onUploaded(attachments);
                    }
                    setTimeout(() => service.deleteFile(file.id), AUTOCLOSE_DELAY);
                } catch (error) {
                    file.hasError = true;
                    setTimeout(() => service.deleteFile(file.id), AUTOCLOSE_DELAY);
                    throw error;
                }
            }
        };
    }
});
