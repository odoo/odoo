import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { KeepLast } from "@web/core/utils/concurrency";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { ImageSelector } from "@html_editor/main/media/media_dialog/image_selector";

import { UnsplashError } from "../unsplash_error/unsplash_error";
import { useState } from "@odoo/owl";

patch(ImageSelector.prototype, {
    setup() {
        super.setup();
        this.unsplash = useService("unsplash");
        this.keepLastUnsplash = new KeepLast();
        this.unsplashState = useState({
            unsplashRecords: [],
            isFetchingUnsplash: false,
            isMaxed: false,
            unsplashError: null,
            useUnsplash: true,
        });

        this.NUMBER_OF_RECORDS_TO_DISPLAY = 30;

        this.errorMessages = {
            key_not_found: {
                title: _t("Setup Unsplash to access royalty free photos."),
                subtitle: "",
            },
            401: {
                title: _t("Unauthorized Key"),
                subtitle: _t("Please check your Unsplash access key and application ID."),
            },
            403: {
                title: _t("Search is temporarily unavailable"),
                subtitle: _t(
                    "The max number of searches is exceeded. Please retry in an hour or extend to a better account."
                ),
            },
        };
    },

    get canLoadMore() {
        if (this.state.searchService === "all") {
            return (
                super.canLoadMore ||
                (this.state.needle &&
                    !this.unsplashState.isMaxed &&
                    !this.unsplashState.unsplashError)
            );
        } else if (this.state.searchService === "unsplash") {
            return (
                this.state.needle &&
                !this.unsplashState.isMaxed &&
                !this.unsplashState.unsplashError
            );
        }
        return super.canLoadMore;
    },

    get hasContent() {
        if (this.state.searchService === "all") {
            return super.hasContent || !!this.unsplashState.unsplashRecords.length;
        } else if (this.state.searchService === "unsplash") {
            return !!this.unsplashState.unsplashRecords.length;
        }
        return super.hasContent;
    },

    get errorTitle() {
        if (this.errorMessages[this.unsplashState.unsplashError]) {
            return this.errorMessages[this.unsplashState.unsplashError].title;
        }
        return _t("Something went wrong");
    },

    get errorSubtitle() {
        if (this.errorMessages[this.unsplashState.unsplashError]) {
            return this.errorMessages[this.unsplashState.unsplashError].subtitle;
        }
        return _t("Please check your internet connection or contact administrator.");
    },

    get selectedRecordIds() {
        return this.props.selectedMedia[this.props.id]
            .filter((media) => media.mediaType === "unsplashRecord")
            .map(({ id }) => id);
    },

    get isFetching() {
        return super.isFetching || this.unsplashState.isFetchingUnsplash;
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
            return [a.map((v, i) => (i < b.length ? [v, b[i]] : v)), b.slice(a.length)].flat(2);
        }
        return alternate(this.unsplashState.unsplashRecords, this.state.libraryMedia);
    },

    get allAttachments() {
        return [...super.allAttachments, ...this.unsplashState.unsplashRecords];
    },

    async fetchUnsplashRecords(offset) {
        if (!this.state.needle) {
            return { records: [], isMaxed: false };
        }
        this.unsplashState.isFetchingUnsplash = true;
        try {
            const { isMaxed, images } = await this.unsplash.getImages(
                this.state.needle,
                offset,
                this.NUMBER_OF_RECORDS_TO_DISPLAY,
                this.props.orientation
            );
            this.unsplashState.isFetchingUnsplash = false;
            this.unsplashState.unsplashError = false;
            // Ignore duplicates.
            const existingIds = this.unsplashState.unsplashRecords.map((existing) => existing.id);
            const newImages = images.filter((record) => !existingIds.includes(record.id));
            const records = newImages.map((record) => {
                const url = new URL(record.urls.regular);
                // In small windows, row height could get quite a bit larger than the min, so we keep some leeway.
                url.searchParams.set("h", 2 * this.MIN_ROW_HEIGHT);
                url.searchParams.delete("w");
                return Object.assign({}, record, {
                    url: url.toString(),
                    mediaType: "unsplashRecord",
                });
            });
            return { isMaxed, records };
        } catch (e) {
            this.unsplashState.isFetchingUnsplash = false;
            if (e === "no_access") {
                this.unsplashState.useUnsplash = false;
            } else {
                this.unsplashState.unsplashError = e;
            }
            return { records: [], isMaxed: true };
        }
    },

    async loadMore(...args) {
        await super.loadMore(...args);
        return this.keepLastUnsplash
            .add(this.fetchUnsplashRecords(this.unsplashState.unsplashRecords.length))
            .then(({ records, isMaxed }) => {
                // This is never reached if another search or loadMore occurred.
                this.unsplashState.unsplashRecords.push(...records);
                this.unsplashState.isMaxed = isMaxed;
            });
    },

    async search(...args) {
        await super.search(...args);
        await this.searchUnsplash();
    },

    async searchUnsplash() {
        if (!this.state.needle) {
            this.unsplashState.unsplashError = false;
            this.unsplashState.unsplashRecords = [];
            this.unsplashState.isMaxed = false;
        }
        return this.keepLastUnsplash
            .add(this.fetchUnsplashRecords(0))
            .then(({ records, isMaxed }) => {
                // This is never reached if a new search occurred.
                this.unsplashState.unsplashRecords = records;
                this.unsplashState.isMaxed = isMaxed;
            });
    },

    async onClickRecord(media) {
        this.props.selectMedia({ ...media, mediaType: "unsplashRecord", query: this.state.needle });
        if (!this.props.multiSelect) {
            await this.props.save();
        }
    },

    async submitCredentials(key, appId) {
        this.unsplashState.unsplashError = null;
        await rpc("/web_unsplash/save_unsplash", { key, appId });
        await this.searchUnsplash();
    },
});

ImageSelector.components = {
    ...ImageSelector.components,
    UnsplashError,
};
