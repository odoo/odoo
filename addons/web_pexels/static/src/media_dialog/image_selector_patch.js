import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { KeepLast } from "@web/core/utils/concurrency";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { ImageSelector } from "@html_editor/main/media/media_dialog/image_selector";

import { PexelsError } from "../pexels_error/pexels_error";
import { useState } from "@odoo/owl";

patch(ImageSelector.prototype, {
    setup() {
        super.setup();
        this.pexels = useService("pexels");
        this.keepLastPexels = new KeepLast();
        this.pexelsState = useState({
            pexelsRecords: [],
            isFetchingPexels: false,
            isMaxed: false,
            pexelsError: null,
            usePexels: true,
        });

        this.NUMBER_OF_RECORDS_TO_DISPLAY = 30;

        this.errorMessages = {
            key_not_found: {
                title: _t("Setup Pexels to access royalty free photos."),
                subtitle: "",
            },
            401: {
                title: _t("Unauthorized Key"),
                subtitle: _t("Please check your Pexels api key."),
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
                    !this.pexelsState.isMaxed &&
                    !this.pexelsState.pexelsError)
            );
        } else if (this.state.searchService === "pexels") {
            return (
                this.state.needle &&
                !this.pexelsState.isMaxed &&
                !this.pexelsState.pexelsError
            );
        }
        return super.canLoadMore;
    },

    get hasContent() {
        if (this.state.searchService === "all") {
            return super.hasContent || !!this.pexelsState.pexelsRecords.length;
        } else if (this.state.searchService === "pexels") {
            return !!this.pexelsState.pexelsRecords.length;
        }
        return super.hasContent;
    },

    get errorTitle() {
        if (this.errorMessages[this.pexelsState.pexelsError]) {
            return this.errorMessages[this.pexelsState.pexelsError].title;
        }
        return _t("Something went wrong");
    },

    get errorSubtitle() {
        if (this.errorMessages[this.pexelsState.pexelsError]) {
            return this.errorMessages[this.pexelsState.pexelsError].subtitle;
        }
        return _t("Please check your internet connection or contact administrator.");
    },

    get selectedRecordIds() {
        return this.props.selectedMedia[this.props.id]
            .filter((media) => media.mediaType === "pexelsRecord")
            .map(({ id }) => id);
    },

    get isFetching() {
        return super.isFetching || this.pexelsState.isFetchingPexels;
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
        return alternate(this.pexelsState.pexelsRecords, this.state.libraryMedia);
    },

    get allAttachments() {
        return [...super.allAttachments, ...this.pexelsState.pexelsRecords];
    },

    async fetchPexelsRecords(offset) {
        if (!this.state.needle) {
            return { records: [], isMaxed: false };
        }
        this.pexelsState.isFetchingPexels = true;
        try {
            const { isMaxed, images } = await this.pexels.getImages(
                this.state.needle,
                offset,
                this.NUMBER_OF_RECORDS_TO_DISPLAY,
                this.props.orientation
            );
            this.pexelsState.isFetchingPexels = false;
            this.pexelsState.pexelsError = false;
            // Ignore duplicates.
            const existingIds = this.pexelsState.pexelsRecords.map((existing) => existing.id);
            const newImages = images.filter((record) => !existingIds.includes(record.id));
            const records = newImages.map((record) => {
                const url = new URL(record.src.large);
                // In small windows, row height could get quite a bit larger than the min, so we keep some leeway.
                url.searchParams.set("h", 2 * this.MIN_ROW_HEIGHT);
                url.searchParams.delete("w");
                return Object.assign({}, record, {
                    url: url.toString(),
                    mediaType: "pexelsRecord",
                });
            });
            return { isMaxed, records };
        } catch (e) {
            this.pexelsState.isFetchingPexels = false;
            if (e === "no_access") {
                this.pexelsState.usePexels = false;
            } else {
                this.pexelsState.pexelsError = e;
            }
            return { records: [], isMaxed: true };
        }
    },

    async loadMore(...args) {
        await super.loadMore(...args);
        return this.keepLastPexels
            .add(this.fetchPexelsRecords(this.pexelsState.pexelsRecords.length))
            .then(({ records, isMaxed }) => {
                // This is never reached if another search or loadMore occurred.
                this.pexelsState.pexelsRecords.push(...records);
                this.pexelsState.isMaxed = isMaxed;
            });
    },

    async search(...args) {
        await super.search(...args);
        await this.searchPexels();
    },

    async searchPexels() {
        if (!this.state.needle) {
            this.pexelsState.pexelsError = false;
            this.pexelsState.pexelsRecords = [];
            this.pexelsState.isMaxed = false;
        }
        return this.keepLastPexels
            .add(this.fetchPexelsRecords(0))
            .then(({ records, isMaxed }) => {
                // This is never reached if a new search occurred.
                this.pexelsState.pexelsRecords = records;
                this.pexelsState.isMaxed = isMaxed;
            });
    },

    async onClickRecord(media) {
        this.props.selectMedia({ ...media, mediaType: "pexelsRecord", query: this.state.needle });
        if (!this.props.multiSelect) {
            await this.props.save();
        }
    },

    async submitCredentials(key, appId) {
        this.pexelsState.pexelsError = null;
        await rpc("/web_pexels/save_pexels", { key, appId });
        await this.searchPexels();
    },
});

ImageSelector.components = {
    ...ImageSelector.components,
    PexelsError,
};
