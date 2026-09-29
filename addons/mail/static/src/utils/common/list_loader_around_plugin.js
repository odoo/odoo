import {
    getLoadedStatus,
    LIST_LOADER_EPOCH,
    LIST_LOADER_STATUS,
    ListLoaderPlugin,
} from "@mail/utils/common/list_loader";

/**
 * @typedef {import("@mail/utils/common/list_loader").ListLoaderEpoch} ListLoaderEpoch
 * @typedef {import("@mail/utils/common/list_loader").ListLoaderRecord} ListLoaderRecord
 */

/**
 * Request parameters added by `LoadAroundPlugin`.
 *
 * @typedef {Object} ListLoaderAroundParams
 * @property {number} [after] id of the record the page is newer than
 * @property {number} [around] id of the record the page is centered on (included)
 * @property {number} [before] id of the record the page is older than
 */

/**
 * Loading of the records around a given record, then of the newer ones, for lists ordered by id
 * server-side (e.g. the messages of a thread).
 *
 * Pages are requested from the oldest/newest loaded record (`before`/`after`), only excluding the
 * known records beyond it, i.e. added out of band (e.g. own posts or received from the bus): the
 * records missed in between are loaded, without sending all the known ids.
 */
export class LoadAroundPlugin extends ListLoaderPlugin {
    static id = "around";
    static shared = ["loadAround"];

    resources = {
        page_params_processors: this.processPageParams.bind(this),
        on_page_loaded_handlers: this.onPageLoaded.bind(this),
    };
    /** @type {number|undefined} lowest id of the contiguous loaded records */
    oldestId;
    /** @type {number|undefined} highest id of the contiguous loaded records */
    newestId;

    /**
     * Reset the loader, then load the records around the record with the given id, or the newest
     * records when no id is given.
     *
     * @param {number} [anchor]
     * @param {Object} [options]
     * @param {number} [options.limit] amount of records, half on each side of the anchor
     * @param {Object} [options.params] extra params, given as is to `fetch`
     * @returns {Promise<ListLoaderRecord[]|undefined>} the fetched records, `undefined` if the
     *  loader was reset again in the meantime.
     */
    async loadAround(anchor, { limit = this.loader.limit, params: extraParams } = {}) {
        this.loader.reset();
        const params = { limit, ...extraParams };
        if (anchor !== undefined) {
            params.around = anchor;
        }
        const records = await this.loader.fetchPage(params, {
            older: true,
            newer: anchor !== undefined,
        });
        if (!records) {
            return;
        }
        let older = getLoadedStatus(records.length, limit);
        let newer = LIST_LOADER_STATUS.LOADED;
        if (anchor !== undefined) {
            // Records up to the anchor (included) fill one half, newer ones the other.
            const half = Math.floor(limit / 2);
            const olderCount = records.filter(({ id }) => id <= anchor).length;
            older = getLoadedStatus(olderCount, half);
            newer = getLoadedStatus(records.length - olderCount, half);
        }
        Object.assign(this.loader.state, { newer, older });
        this.oldestId = this.newestId = undefined;
        this._extendBounds(records.map(({ id }) => id));
        return records;
    }

    /**
     * @param {import("@mail/utils/common/list_loader").ListLoaderParams & ListLoaderAroundParams} params
     * @param {ListLoaderEpoch} epoch
     */
    processPageParams(params, epoch) {
        const isOlder = epoch === LIST_LOADER_EPOCH.OLDER;
        const cursor = isOlder ? this.oldestId : this.newestId;
        if (cursor === undefined) {
            return;
        }
        params[isOlder ? "before" : "after"] = cursor;
        const excludeIds = params.exclude_ids?.filter((id) =>
            isOlder ? id < cursor : id > cursor
        );
        if (excludeIds?.length) {
            params.exclude_ids = excludeIds;
        } else {
            delete params.exclude_ids;
        }
    }

    /**
     * @param {Object} page
     * @param {ListLoaderEpoch} page.epoch
     * @param {import("@mail/utils/common/list_loader").ListLoaderParams} page.params
     * @param {ListLoaderRecord[]} page.records
     */
    onPageLoaded({ epoch, params, records }) {
        const ids = records.map(({ id }) => id);
        if (this.loader.state[epoch] === LIST_LOADER_STATUS.LOADED) {
            // Nothing else on this side: the excluded records are contiguous to the loaded ones,
            // and need not be excluded from the next pages.
            ids.push(...(params.exclude_ids ?? []));
        }
        this._extendBounds(ids);
    }

    /** @param {number[]} ids ids of records contiguous to the loaded ones */
    _extendBounds(ids) {
        if (ids.length) {
            this.oldestId = Math.min(this.oldestId ?? Infinity, ...ids);
            this.newestId = Math.max(this.newestId ?? -Infinity, ...ids);
        }
    }
}
