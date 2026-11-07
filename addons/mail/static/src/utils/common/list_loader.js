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
export function getLoadedStatus(count, limit) {
    return count < limit ? LIST_LOADER_STATUS.LOADED : LIST_LOADER_STATUS.IDLE;
}

/**
 * @typedef {typeof LIST_LOADER_EPOCH[keyof typeof LIST_LOADER_EPOCH]} ListLoaderEpoch
 * @typedef {typeof LIST_LOADER_STATUS[keyof typeof LIST_LOADER_STATUS]} ListLoaderStatus
 * @typedef {{ id: number }} ListLoaderRecord a record of the list
 */

/**
 * Request parameters of a page, plus the extra `params` given to the load. Plugins can add their
 * own, e.g. `LoadAroundPlugin`.
 *
 * @typedef {Object} ListLoaderParams
 * @property {number} limit amount of records
 * @property {number[]} [exclude_ids] ids of the records to skip, already known
 */

/**
 * Hooks that plugins provide to a `ListLoader` through their `resources`.
 *
 * @typedef {Object} ListLoaderResources
 * @property {(params: ListLoaderParams, epoch: ListLoaderEpoch) => void} page_params_processors
 *  adapt the request parameters of a page before it is fetched.
 * @property {(page: { epoch: ListLoaderEpoch, params: ListLoaderParams, records: ListLoaderRecord[] }) => void} on_page_loaded_handlers
 *  called once a page is loaded, its side status being updated.
 */

/**
 * Feature of a `ListLoader`, enabled by giving its class to the loader, like the plugins of the
 * html editor: it hooks into the loader through its `resources` (see `ListLoaderResources`), and
 * exposes its `shared` methods on `loader.shared[id]`.
 */
export class ListLoaderPlugin {
    static id = "";
    /** @type {string[]} names of the methods available on `loader.shared[id]` */
    static shared = [];

    /** @type {Partial<ListLoaderResources>} */
    resources = {};

    /** @param {ListLoader} loader */
    constructor(loader) {
        this.loader = loader;
    }
}

/**
 * Hole-free lazy loading of a list of records, ordered newest first server-side.
 *
 * Pages exclude the records already known client-side (`exclude_ids`): the server returns the
 * closest records not known yet. Records added, moved or missed meanwhile are thus not skipped,
 * without knowing the sort key.
 *
 * E.g. channels ordered by last interest, the first 30 loaded: an unloaded channel receives a
 * message and moves above them. A cursor after the 30th channel would skip it, whereas the next
 * page (top channels, excluding the 30 known ones) returns it.
 *
 * Only older pages are loaded by default, the newest records being loaded first. Plugins add
 * other ways of loading, e.g. `LoadAroundPlugin`.
 */
export class ListLoader {
    /**
     * @param {Object} options
     * @param {(params: ListLoaderParams) => Promise<ListLoaderRecord[]>} options.fetch fetches the
     *  records, see `ListLoaderParams`.
     * @param {() => number[]} options.getKnownIds ids of the records of the list already known
     *  client-side, excluded from the requests.
     * @param {number} options.limit default amount of records per page
     * @param {typeof ListLoaderPlugin[]} [options.Plugins] features of this loader
     */
    constructor({ fetch, getKnownIds, limit, Plugins = [] }) {
        this.fetch = fetch;
        this.getKnownIds = getKnownIds;
        this.limit = limit;
        this.state = proxy({
            /** Bumped on reset, to discard the responses requested before it. */
            resetCount: 0,
            loadingNewer: false,
            loadingOlder: false,
            /** @type {ListLoaderStatus} */
            newer: LIST_LOADER_STATUS.LOADED,
            /** @type {ListLoaderStatus} */
            older: LIST_LOADER_STATUS.NEW,
        });
        this.plugins = Plugins.map((P) => new P(this));
        /** @type {Object<string, Object<string, Function>>} */
        this.shared = {};
        for (const plugin of this.plugins) {
            const P = plugin.constructor;
            this.shared[P.id] = Object.fromEntries(
                P.shared.map((name) => [name, plugin[name].bind(plugin)])
            );
        }
    }

    /**
     * @template {keyof ListLoaderResources} K
     * @param {K} name
     * @returns {ListLoaderResources[K][]}
     */
    getResource(name) {
        return this.plugins.map((plugin) => plugin.resources[name]).filter(Boolean);
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
     * Load the next page on the given side. Loading a fully loaded side requires `force`, e.g. to
     * catch up on records that were possibly missed.
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
        const isLoading = this.getStatus(epoch) === LIST_LOADER_STATUS.LOADING;
        if (isLoading || (!force && !this.canLoad(epoch))) {
            return;
        }
        const params = { limit, ...extraParams };
        const knownIds = this.getKnownIds();
        if (knownIds.length) {
            params.exclude_ids = knownIds;
        }
        for (const processParams of this.getResource("page_params_processors")) {
            processParams(params, epoch);
        }
        const isOlder = epoch === LIST_LOADER_EPOCH.OLDER;
        const records = await this.fetchPage(params, { older: isOlder, newer: !isOlder });
        if (records) {
            this.state[epoch] = getLoadedStatus(records.length, limit);
            for (const onPageLoaded of this.getResource("on_page_loaded_handlers")) {
                onPageLoaded({ epoch, params, records });
            }
        }
        return records;
    }

    /** Discard the responses of the pending loads, e.g. before loading another part of the list. */
    reset() {
        this.state.resetCount++;
        Object.assign(this.state, { loadingNewer: false, loadingOlder: false });
    }

    /** Mark both sides as fully loaded, e.g. when the list is known to be empty. */
    markFullyLoaded() {
        this.state.older = LIST_LOADER_STATUS.LOADED;
        this.state.newer = LIST_LOADER_STATUS.LOADED;
    }

    /**
     * @param {ListLoaderParams} params
     * @param {{ older: boolean, newer: boolean }} loading sides being loaded
     * @returns {Promise<ListLoaderRecord[]|undefined>} `undefined` if the loader was reset
     *  during the fetch.
     */
    async fetchPage(params, { older, newer }) {
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
