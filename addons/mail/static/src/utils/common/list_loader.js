import { proxy } from "@odoo/owl";

/**
 * @typedef {"older"|"newer"} ListLoaderEpoch
 * @typedef {"new"|"idle"|"loaded"} ListLoaderStatus
 * - `new`: nothing loaded yet on this side,
 * - `idle`: more records may be loaded on this side,
 * - `loaded`: every record on this side is loaded.
 *
 * @typedef {{ id: number }} ListLoaderRecord a record of the list, e.g. a message
 */

/**
 * Request parameters, named after `mail.message._message_fetch`, plus the extra `params`
 * given to the load.
 *
 * @typedef {Object} ListLoaderParams
 * @property {number} limit
 * @property {number} [after]
 * @property {number} [around]
 * @property {number} [before]
 * @property {number[]} [exclude_ids]
 */

/**
 * Hole-free lazy loading of a list of records, ordered newest first server-side.
 *
 * The loaded records form a single contiguous window of the list, either loaded from the newest
 * record, or loaded around a reference record (`anchor`). Each page is requested from the far end
 * of the window rather than from the edge it extends, and excludes the records already known
 * (`exclude_ids`): the server returns the closest records that are not known yet. Compared to a
 * cursor on the last loaded record, this avoids holes when the list changed in the meantime:
 * records known out of band (bus, own post, other filters of the same list) are skipped instead of
 * being taken as the edge of the window, records missing inside the window are returned by the
 * next page, and records whose sort key changed are neither skipped nor duplicated. It also
 * doesn't require the client to know the server-side order when loading older records from the
 * newest one (e.g. channels ordered by last interest).
 *
 * Loading newer records or around a record requires the list to be ordered by id server-side
 * (e.g. messages), as the far end is given by id. Such lists should set `orderedById`, so that
 * older records loaded from the newest one are bounded by the newest known record: otherwise,
 * records added since the window was loaded would be returned first, leaving a hole below them
 * when they don't fit in a page.
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
            /** @type {number|undefined} reference record of a window loaded around it */
            anchor: undefined,
            /** Bumped when the window is replaced, to discard responses for the previous one. */
            generation: 0,
            loading: { older: false, newer: false },
            /** @type {ListLoaderStatus} */
            newer: "loaded",
            /** @type {ListLoaderStatus} */
            older: "new",
            /** @type {number|undefined} highest id loaded in the window */
            newestId: undefined,
            /** @type {number|undefined} lowest id loaded in the window */
            oldestId: undefined,
        });
    }

    /**
     * @param {ListLoaderEpoch} epoch
     * @returns {ListLoaderStatus|"loading"}
     */
    getStatus(epoch) {
        return this.state.loading[epoch] ? "loading" : this.state[epoch];
    }

    /** @param {ListLoaderEpoch} epoch */
    canLoad(epoch) {
        return ["new", "idle"].includes(this.getStatus(epoch));
    }

    /**
     * Load the next page on the given side of the window. Loading newer records of a window
     * loaded from the newest record requires `force`, e.g. to catch up on records that were
     * possibly missed.
     *
     * @param {ListLoaderEpoch} [epoch="older"]
     * @param {Object} [options]
     * @param {boolean} [options.force] load even if the side is fully loaded
     * @param {number} [options.limit]
     * @param {Object} [options.params] extra params, given as is to `fetch`
     * @returns {Promise<ListLoaderRecord[]|undefined>} the fetched records, `undefined` if nothing
     *  was loaded or if the window was replaced in the meantime (the records would not be
     *  contiguous to it).
     */
    async load(epoch = "older", { force = false, limit = this.limit, params: extraParams } = {}) {
        const state = this.state;
        if (state.loading[epoch] || (!force && !this.canLoad(epoch))) {
            return;
        }
        // Older records: from the anchor, or from the newest record (the newest known one when
        // ordered by id). Newer records: from the anchor, or from the oldest loaded record.
        let knownIds = this.getKnownIds();
        let farEnd = state.anchor;
        if (epoch === "older" && this.orderedById && state.newestId !== undefined) {
            // Records known out of band (e.g. own post) are part of the window: records missed
            // below them are loaded too.
            farEnd ??= Math.max(state.newestId, ...knownIds) + 1;
        }
        if (epoch === "newer") {
            farEnd ??= state.oldestId;
            if (farEnd === undefined) {
                return this.loadAround(undefined, { limit, params: extraParams });
            }
        }
        const params = { limit, ...extraParams };
        if (farEnd !== undefined) {
            params[epoch === "older" ? "before" : "after"] = farEnd;
            knownIds = knownIds.filter((id) => (epoch === "older" ? id < farEnd : id > farEnd));
        }
        if (knownIds.length) {
            params.exclude_ids = knownIds;
        }
        const records = await this._fetch(params, { [epoch]: true });
        if (records) {
            state[epoch] = records.length < limit ? "loaded" : "idle";
            this._updateBounds(records);
        }
        return records;
    }

    /**
     * Replace the window by the one around the record with the given id, or by the newest
     * records when no id is given.
     *
     * @param {number} [anchor]
     * @param {Object} [options]
     * @param {number} [options.limit] amount of records, half on each side of the anchor
     * @param {Object} [options.params] extra params, given as is to `fetch`
     * @returns {Promise<ListLoaderRecord[]|undefined>} the fetched records, `undefined` if the
     *  window was replaced again in the meantime.
     */
    async loadAround(anchor, { limit = this.limit, params: extraParams } = {}) {
        const state = this.state;
        // Responses of pending loads are discarded, and so are their loading flags.
        state.generation++;
        state.loading = { older: false, newer: false };
        const params = { limit, ...extraParams };
        if (anchor !== undefined) {
            params.around = anchor;
        }
        const records = await this._fetch(params, { older: true, newer: anchor !== undefined });
        if (!records) {
            return;
        }
        let older = records.length < limit ? "loaded" : "idle";
        let newer = "loaded";
        if (anchor !== undefined) {
            // Records up to the anchor (included) fill one half, newer ones the other.
            const half = Math.floor(limit / 2);
            const olderCount = records.filter(({ id }) => id <= anchor).length;
            older = olderCount < half ? "loaded" : "idle";
            newer = records.length - olderCount < half ? "loaded" : "idle";
        }
        Object.assign(state, { anchor, newer, older, newestId: undefined, oldestId: undefined });
        this._updateBounds(records);
        return records;
    }

    /** Mark both sides as fully loaded, e.g. when the list is known to be empty. */
    markFullyLoaded() {
        this.state.older = "loaded";
        this.state.newer = "loaded";
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
     * @param {{ older?: boolean, newer?: boolean }} loading sides being loaded
     * @returns {Promise<ListLoaderRecord[]|undefined>} `undefined` if the window was replaced
     *  during the fetch.
     */
    async _fetch(params, loading) {
        const state = this.state;
        const generation = state.generation;
        Object.assign(state.loading, loading);
        try {
            const records = await this.fetch(params);
            return state.generation === generation ? records : undefined;
        } finally {
            if (state.generation === generation) {
                for (const epoch of Object.keys(loading)) {
                    state.loading[epoch] = false;
                }
            }
        }
    }
}
