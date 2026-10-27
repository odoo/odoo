import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { KeepLast } from "@web/core/utils/concurrency";
import { MediaDialog, TABS } from "@web_editor/components/media_dialog/media_dialog";
import { ImageSelector } from "@web_editor/components/media_dialog/image_selector";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { PexelsError } from "../pexels_error/pexels_error";

patch(ImageSelector.prototype, {
    setup() {
        super.setup();
        this.pexels = useService('pexels');
        this.keepLastPexels = new KeepLast();

        this.state.pexelsRecords = [];
        this.state.isFetchingPexels = false;
        this.state.isMaxed = false;
        this.state.pexelsError = null;
        this.state.usePexels = true;
        this.NUMBER_OF_RECORDS_TO_DISPLAY = 30;

        this.errorMessages = {
            'key_not_found': {
                title: _t("Setup Pexels to access royalty free photos."),
                subtitle: "",
            },
            401: {
                title: _t("Unauthorized Key"),
                subtitle: _t("Please check your Pexels access key and application ID."),
            },
            403: {
                title: _t("Search is temporarily unavailable"),
                subtitle: _t("The max number of searches is exceeded. Please retry in an hour or extend to a better account."),
            },
        };
    },

    get canLoadMore() {
        if (this.state.searchService === 'all') {
            return super.canLoadMore || this.state.needle && !this.state.isMaxed && !this.state.pexelsError;
        } else if (this.state.searchService === 'pexels') {
            return this.state.needle && !this.state.isMaxed && !this.state.pexelsError;
        }
        return super.canLoadMore;
    },

    get hasContent() {
        if (this.state.searchService === 'all') {
            return super.hasContent || !!this.state.pexelsRecords.length;
        } else if (this.state.searchService === 'pexels') {
            return !!this.state.pexelsRecords.length;
        }
        return super.hasContent;
    },

    get errorTitle() {
        if (this.errorMessages[this.state.pexelsError]) {
            return this.errorMessages[this.state.pexelsError].title;
        }
        return _t("Something went wrong");
    },

    get errorSubtitle() {
        if (this.errorMessages[this.state.pexelsError]) {
            return this.errorMessages[this.state.pexelsError].subtitle;
        }
        return _t("Please check your internet connection or contact administrator.");
    },

    get selectedRecordIds() {
        return this.props.selectedMedia[this.props.id].filter(media => media.mediaType === 'pexelsRecord').map(({ id }) => id);
    },

    get isFetching() {
        return super.isFetching || this.state.isFetchingPexels;
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
        return alternate(this.state.pexelsRecords, this.state.libraryMedia);
    },

    get allAttachments() {
        return [...super.allAttachments, ...this.state.pexelsRecords];
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

    async fetchPexelsRecords(offset) {
        if (!this.state.needle) {
            return { records: [], isMaxed: false };
        }
        this.state.isFetchingPexels = true;
        try {
            const { isMaxed, images } = await this.pexels.getImages(this.state.needle, offset, this.NUMBER_OF_RECORDS_TO_DISPLAY, this.props.orientation);
            this.state.isFetchingPexels = false;
            this.state.pexelsError = false;
            // Ignore duplicates.
            const existingIds = this.state.pexelsRecords.map(existing => existing.id);
            const newImages = images.filter(record => !existingIds.includes(record.id));
            const records = newImages.map(record => {
                const url = new URL(record.src.large);
                // In small windows, row height could get quite a bit larger than the min, so we keep some leeway.
                url.searchParams.set('h', 2 * this.MIN_ROW_HEIGHT);
                url.searchParams.delete('w');
                return Object.assign({}, record, {
                    url: url.toString(),
                    mediaType: 'pexelsRecord',
                });
            });
            return { isMaxed, records };
        } catch (e) {
            this.state.isFetchingPexels = false;
            if (e === 'no_access') {
                this.state.usePexels = false;
            } else {
                this.state.pexelsError = e;
            }
            return { records: [], isMaxed: true };
        }
    },

    async loadMore(...args) {
        await super.loadMore(...args);
        return this.keepLastPexels.add(this.fetchPexelsRecords(this.state.pexelsRecords.length)).then(({ records, isMaxed }) => {
            // This is never reached if another search or loadMore occurred.
            this.state.pexelsRecords.push(...records);
            this.state.isMaxed = isMaxed;
        });
    },

    async search(...args) {
        await super.search(...args);
        await this.searchPexels();
    },

    async searchPexels() {
        if (!this.state.needle) {
            this.state.pexelsError = false;
            this.state.pexelsRecords = [];
            this.state.isMaxed = false;
        }
        return this.keepLastPexels.add(this.fetchPexelsRecords(0)).then(({ records, isMaxed }) => {
            // This is never reached if a new search occurred.
            this.state.pexelsRecords = records;
            this.state.isMaxed = isMaxed;
        });
    },

    async onClickRecord(media) {
        this.props.selectMedia({ ...media, mediaType: 'pexelsRecord', query: this.state.needle });
        if (!this.props.multiSelect) {
            await this.props.save();
        }
    },

    async submitCredentials(key, appId) {
        this.state.pexelsError = null;
        await rpc('/web_pexels/save_pexels', { key, appId });
        await this.searchPexels();
    },
});
ImageSelector.components = {
    ...ImageSelector.components,
    PexelsError,
};

patch(MediaDialog.prototype, {
    setup() {
        super.setup();

        this.pexelsService = useService('pexels');
    },

    async save() {
        const selectedImages = this.selectedMedia[TABS.IMAGES.id];
        if (selectedImages) {
            const pexelsRecords = selectedImages.filter(media => media.mediaType === 'pexelsRecord');
            if (pexelsRecords.length) {
                await this.pexelsService.uploadPexelsRecords(pexelsRecords, { resModel: this.props.resModel, resId: this.props.resId }, (attachments) => {
                    this.selectedMedia[TABS.IMAGES.id] = this.selectedMedia[TABS.IMAGES.id].filter(media => media.mediaType !== 'pexelsRecord');
                    this.selectedMedia[TABS.IMAGES.id] = this.selectedMedia[TABS.IMAGES.id].concat(attachments.map(attachment => ({...attachment, mediaType: 'attachment'})));
                });
            }
        }
        return super.save(...arguments);
    },
});
