import { proxy } from "@odoo/owl";

export const LIST_LOADER_EPOCH = Object.freeze({
    OLDER: "older",
    NEWER: "newer",
});

export const LIST_LOADER_STATUS = Object.freeze({
    /** Nothing loaded yet on this side. */
    NEW: "new",
    /** More records may be loaded on this side. */
    IDLE: "idle",
    /** A page is being loaded on this side, only returned by `getStatus`. */
    LOADING: "loading",
    /** Every record on this side is loaded. */
    LOADED: "loaded",
});

/**
 * @param {number} count amount of records loaded on a side
 * @param {number} limit amount of records requested on that side
 * @returns {ListLoaderStatus} `LOADED` when the server returned less than requested
 */
function getLoadedStatus(count, limit) {
    return count < limit ? LIST_LOADER_STATUS.LOADED : LIST_LOADER_STATUS.IDLE;
}

/**
 * @typedef {typeof LIST_LOADER_EPOCH[keyof typeof LIST_LOADER_EPOCH]} ListLoaderEpoch
 * @typedef {typeof LIST_LOADER_STATUS[keyof typeof LIST_LOADER_STATUS]} ListLoaderStatus
 * @typedef {{ id: number }} ListLoaderRecord a record of the list
 */

/**
 * Request parameters of a page, plus the extra `params` given to the load.
 *
 * @typedef {Object} ListLoaderParams
 * @property {number} limit amount of records
 * @property {number} [after] id of the record the page is newer than
 * @property {number} [around] id of the record the page is centered on (included)
 * @property {number} [before] id of the record the page is older than
 * @property {number[]} [exclude_ids] ids of the records to skip, already known
 */

/**
 * Hole-free lazy loading of a list of records, ordered newest first server-side.
 *
 * Records are loaded from the newest one or around a reference record (`anchor`). Each page is
 * requested from the far end of the loaded records rather than from the edge it extends,
 * excluding the known ones (`exclude_ids`): the server returns the closest records not known yet.
 * Records added, moved or missed meanwhile are thus not skipped, without knowing the sort key.
 *
 * E.g. channels ordered by last interest, the first 30 loaded: an unloaded channel receives a
 * message and moves above them. A cursor after the 30th channel would skip it, whereas the next
 * page (top channels, excluding the 30 known ones) returns it.
 *
 * Loading newer records or around a record requires the list to be ordered by id server-side.
 * Such lists should set `orderedById`, so that older records are bounded by the newest known one
 * instead of starting with records added since the loader was reset.
 */
export class ListLoader {
    /**
     * @param {Object} options
     * @param {(params: ListLoaderParams) => Promise<ListLoaderRecord[]>} options.fetch fetches the
     *  records, see `ListLoaderParams`.
     * @param {() => number[]} options.getKnownIds ids of the records of the list already known
     *  client-side, excluded from the requests.
     * @param {number} options.limit default amount of records per page
     * @param {boolean} [options.orderedById] whether the list is ordered by id server-side
     */
    constructor({ fetch, getKnownIds, limit, orderedById = false }) {
        this.fetch = fetch;
        this.getKnownIds = getKnownIds;
        this.limit = limit;
        this.orderedById = orderedById;
        this.state = proxy({
            /** @type {number|undefined} reference record the records are loaded around */
            anchor: undefined,
            /** Bumped on reset, to discard the responses requested before it. */
            resetCount: 0,
            loadingNewer: false,
            loadingOlder: false,
            /** @type {ListLoaderStatus} */
            newer: LIST_LOADER_STATUS.LOADED,
            /** @type {ListLoaderStatus} */
            older: LIST_LOADER_STATUS.NEW,
            /** @type {number|undefined} highest id loaded */
            newestId: undefined,
            /** @type {number|undefined} lowest id loaded */
            oldestId: undefined,
        });
    }

    /**
     * @param {ListLoaderEpoch} epoch
     * @returns {ListLoaderStatus}
     */
    getStatus(epoch) {
        const state = this.state;
        const isLoading =
            epoch === LIST_LOADER_EPOCH.OLDER ? state.loadingOlder : state.loadingNewer;
        return isLoading ? LIST_LOADER_STATUS.LOADING : state[epoch];
    }

    /** @param {ListLoaderEpoch} epoch */
    canLoad(epoch) {
        return [LIST_LOADER_STATUS.NEW, LIST_LOADER_STATUS.IDLE].includes(this.getStatus(epoch));
    }

    /**
     * Load the next page on the given side. Loading newer records when loaded from the newest
     * record requires `force`, e.g. to catch up on records that were possibly missed.
     *
     * @param {ListLoaderEpoch} [epoch=LIST_LOADER_EPOCH.OLDER]
     * @param {Object} [options]
     * @param {boolean} [options.force] load even if the side is fully loaded
     * @param {number} [options.limit]
     * @param {Object} [options.params] extra params, given as is to `fetch`
     * @returns {Promise<ListLoaderRecord[]|undefined>} the fetched records, `undefined` if nothing
     *  was loaded or if the loader was reset in the meantime (the records would not be
     *  contiguous to the loaded ones).
     */
    async load(
        epoch = LIST_LOADER_EPOCH.OLDER,
        { force = false, limit = this.limit, params: extraParams } = {}
    ) {
        const state = this.state;
        const isOlder = epoch === LIST_LOADER_EPOCH.OLDER;
        const isLoading = this.getStatus(epoch) === LIST_LOADER_STATUS.LOADING;
        if (isLoading || (!force && !this.canLoad(epoch))) {
            return;
        }
        // From the anchor, else from the newest record (older) or the oldest loaded one (newer).
        let knownIds = this.getKnownIds();
        let farEnd = state.anchor;
        if (isOlder && this.orderedById && state.newestId !== undefined) {
            // Above records known out of band, to also load the ones missed below them.
            farEnd ??= Math.max(state.newestId, ...knownIds) + 1;
        }
        if (!isOlder) {
            farEnd ??= state.oldestId;
            if (farEnd === undefined) {
                return this.loadAround(undefined, { limit, params: extraParams });
            }
        }
        const params = { limit, ...extraParams };
        if (farEnd !== undefined) {
            params[isOlder ? "before" : "after"] = farEnd;
            knownIds = knownIds.filter((id) => (isOlder ? id < farEnd : id > farEnd));
        }
        if (knownIds.length) {
            params.exclude_ids = knownIds;
        }
        const records = await this._fetch(params, { older: isOlder, newer: !isOlder });
        if (records) {
            state[epoch] = getLoadedStatus(records.length, limit);
            this._updateBounds(records);
        }
        return records;
    }

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
    async loadAround(anchor, { limit = this.limit, params: extraParams } = {}) {
        const state = this.state;
        // Responses of pending loads are discarded, and so are their loading flags.
        state.resetCount++;
        Object.assign(state, { loadingNewer: false, loadingOlder: false });
        const params = { limit, ...extraParams };
        if (anchor !== undefined) {
            params.around = anchor;
        }
        const records = await this._fetch(params, { older: true, newer: anchor !== undefined });
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
        Object.assign(state, { anchor, newer, older, newestId: undefined, oldestId: undefined });
        this._updateBounds(records);
        return records;
    }

    /** Mark both sides as fully loaded, e.g. when the list is known to be empty. */
    markFullyLoaded() {
        this.state.older = LIST_LOADER_STATUS.LOADED;
        this.state.newer = LIST_LOADER_STATUS.LOADED;
    }

    /**
     * Extend `oldestId`/`newestId` to the given records, the far ends of newer/older loads.
     *
     * @param {ListLoaderRecord[]} records newly loaded records
     */
    _updateBounds(records) {
        const ids = records.map(({ id }) => id);
        if (ids.length) {
            this.state.oldestId = Math.min(this.state.oldestId ?? Infinity, ...ids);
            this.state.newestId = Math.max(this.state.newestId ?? -Infinity, ...ids);
        }
    }

    /**
     * @param {ListLoaderParams} params
     * @param {{ older: boolean, newer: boolean }} loading sides being loaded
     * @returns {Promise<ListLoaderRecord[]|undefined>} `undefined` if the loader was reset
     *  during the fetch.
     */
    async _fetch(params, { older, newer }) {
        const state = this.state;
        const resetCount = state.resetCount;
        if (older) {
            state.loadingOlder = true;
        }
        if (newer) {
            state.loadingNewer = true;
        }
        try {
            const records = await this.fetch(params);
            return state.resetCount === resetCount ? records : undefined;
        } finally {
            if (state.resetCount === resetCount && older) {
                state.loadingOlder = false;
            }
            if (state.resetCount === resetCount && newer) {
                state.loadingNewer = false;
            }
        }
    }
}
