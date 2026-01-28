import { markRaw } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { ConnectionLostError, rpc, rpcBus } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { IndexedDB } from "@web/core/utils/indexed_db";
import { Reactive } from "@web/core/utils/reactive";
import { session } from "@web/session";
import { hashCode } from "../utils/strings";

const IS_READY = Symbol("ready");

class OfflineManager extends Reactive {
    static VISITED_UI_TABLE_NAME = "visited-ui-items";
    static VISITED_UI_TABLE_NAME_DEBUG = "visited-ui-items-debug";
    static ORM_SYNC_TABLE_NAME = "orm-to-sync";

    static SELECTORS_TO_DISABLE = ["button:not([data-available-offline]):not([disabled])"];

    constructor(env, { orm }) {
        super(...arguments);

        this.env = env;
        this.orm = orm;
        this._idb = markRaw(new IndexedDB("offline", session.registry_hash));
        this._visitedUITable = this.env.debug
            ? OfflineManager.VISITED_UI_TABLE_NAME_DEBUG
            : OfflineManager.VISITED_UI_TABLE_NAME;
        this._visited = {}; // stores items that are available offline (only populated when offline)
        this._visited[IS_READY] = null;
        this._ormToSync = {}; // store items that need to be sync once we go online.
        this._timeout = null; // used to repeatedly ping the server when offline
        this._observer = null; // used to detect DOM mutations and disable the UI when offline
        this._offline = false;

        // Use "offline" and "online" events for instant detection of connection lost/restored.
        browser.addEventListener("offline", () => {
            if (!this.offline) {
                this.checkConnection();
            }
        });
        browser.addEventListener("online", () => {
            if (this.offline) {
                this.checkConnection();
            }
        });

        // Use RPC:RESPONSE to validate the current offline status, which is more accurate than
        // the "offline"/"online" events (e.g. server is down).
        rpcBus.addEventListener("RPC:RESPONSE", async (ev) => {
            this.offline = ev.detail.error instanceof ConnectionLostError;
        });

        // When the "CLEAR-CACHES" event is triggered, the rpc cache is wiped out, so we must also
        // clear the information about elements that are available offline, as they aren't anymore.
        rpcBus.addEventListener("CLEAR-CACHES", () => {
            this._idb.invalidate([
                OfflineManager.VISITED_UI_TABLE_NAME,
                OfflineManager.VISITED_UI_TABLE_NAME_DEBUG,
            ]);
            this._visited = {};
        });

        this._updateScheduledORMList().then(async () => {
            if (!this._offline) {
                await new Promise((r) => browser.setTimeout(r, 3000)); // Waits 3 second
                this._syncORM();
            }
        });
    }

    get offline() {
        return this._offline;
    }

    /**
     * Sets the offline status.
     *
     * If we're going offline, we must get the information about actions, views, records that
     * are available offline before toggling the status, such that the rest of the UI can
     * synchronously access the information when rendering offline. As reading from indexeddb
     * is async, we read everything once, and store it in an plain object. We also ensure that
     * buttons and inputs in the UI that haven't been tagged as "available-offline" are
     * disabled while being offline. Finally, we repeatedly try to ping the server to detect if
     * connection is back.
     *
     * If we're going online, we re-enable the UI and update the offline status.
     *
     * @param {boolean} offline
     */
    set offline(offline) {
        if (offline === this._offline) {
            return;
        }
        this._offline = offline;
        this._visited = {};
        if (offline) {
            // Disable everything in the UI that isn't marked as available offline.
            this._offlineUI();
            // Create an observer instance linked to the callback function to keep disabling
            // elements that would appear in the DOM while being offline.
            this._observer = new MutationObserver(() => {
                if (this._offline) {
                    this._offlineUI();
                }
            });
            this._observer.observe(document.body, {
                childList: true, // listen for direct children being added/removed
                subtree: true, // also observe descendants (not just direct children)
                attributeFilter: ["data-available-offline"], // listen for specific attribute change
            });

            // Repeatedly check if connection is back.
            let delay = 2000;
            const _checkConnection = async () => {
                if (this._offline) {
                    await this.checkConnection();
                    // exponential backoff, with some jitter
                    delay = delay * 1.5 + 500 * Math.random();
                    this._timeout = browser.setTimeout(_checkConnection, delay);
                }
            };
            this._timeout = browser.setTimeout(_checkConnection, delay);

            // Retrieve the information about visited items from indexeddb.
            this._visited[IS_READY] = this._populateVisited();
        } else {
            this._onlineUI();
            this._syncORM();
            this._observer?.disconnect();
            browser.clearTimeout(this._timeout);
        }
    }

    /**
     * Pings the server to check if it is reachable.
     */
    async checkConnection() {
        try {
            await rpc("/web/webclient/version_info", {});
        } catch {
            // just catch the error, the offline status will be updated with RPC:RESPONSE
        }
    }

    /**
     * Returns search queries that are available offline, their facets and the number of times they
     * have been accessed, given an action id and a view type.
     *
     * @param {number} actionId
     * @param {"kanban"|"list"}
     * @returns Promise<Object[]>
     */
    async getAvailableSearches(actionId, viewType) {
        await this._visited[IS_READY];
        if (!this._visited[actionId]?.views[viewType]) {
            return [];
        } else if (this._visited[actionId]?.views[viewType] === true) {
            // Searches for that action/view type haven't been retrieve from idb yet
            this._visited[actionId].views[viewType] = this._idb
                .read(this._visitedUITable, this._generateKey(actionId, viewType))
                .then((r) =>
                    Object.values(r || {})
                        .reverse() // last visited first
                        .sort(({ count: c1 }, { count: c2 }) => c2 - c1)
                        .map(({ search }) => search)
                );
        }
        const searches = await this._visited[actionId]?.views[viewType];
        return [...searches];
    }

    /**
     * Returns a boolean indicating whether the requested element is available offline, i.e.
     * if it has been visited online and stored in cache.
     *
     * @param {number} actionId
     * @param {"kanban"|"list"|"form"} [viewType]
     * @param {number} [resId]
     * @returns boolean
     */
    isAvailableOffline(actionId, viewType, resId) {
        const action = this._visited[actionId];
        if (!viewType) {
            return !!action;
        }
        const view = action?.views[viewType];
        if (viewType !== "form") {
            return !!view;
        }
        return view?.includes(resId);
    }

    /**
     * Mark an action, view type and optionally record as available offline.
     *
     * @param {number} actionId
     * @param {"kanban"|"list"|"form"} viewType
     * @param {Object} params
     * @param {number} [params.resId] the record id, when viewType is "form"
     * @param {Object} [params.search] the current search view state
     */
    async setAvailableOffline(actionId, viewType, { resId, search }) {
        if (!this.offline) {
            const key = this._generateKey(actionId, viewType, resId);
            let value;
            if (viewType.startsWith("form")) {
                value = true;
            } else {
                value = (await this._idb.read(this._visitedUITable, key)) || {};
                let count = value[search.key]?.count || 0;
                delete value[search.key]; // delete and re-add to mark it as "last visited"
                value[search.key] = { count: ++count, search };
            }
            return this._idb.write(this._visitedUITable, key, value);
        }
    }

    // -------------------------------------------------------------------------
    // ORM Offline
    // -------------------------------------------------------------------------

    async scheduleORM(model, method, args, kwargs, options) {
        const value = { model, method, args, kwargs, extras: options.extras };
        const key = options.id ?? hashCode(JSON.stringify(value));
        this._ormToSync[key] = { key, value };
        this._idb.write(OfflineManager.ORM_SYNC_TABLE_NAME, key, JSON.stringify(value));
        return key;
    }

    async removeScheduledORM(key) {
        delete this._ormToSync[key];
        this._idb.delete(OfflineManager.ORM_SYNC_TABLE_NAME, key);
    }

    get scheduledORM() {
        return this._ormToSync;
    }

    get hasScheduledCalls() {
        return !!Object.keys(this._ormToSync).length;
    }

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------

    /**
     * Generates the key to identify an action, a viewType and optionally a record
     * id, to use as key in the indexeddb table.
     *
     * @private
     * @param {number} actionId
     * @param {"kanban"|"list"|"form"} viewType
     * @param {number} [params.resId] the record id, when viewType is "form"
     * @returns string
     */
    _generateKey(actionId, viewType, resId) {
        return JSON.stringify({ action: actionId, viewType, resId });
    }

    /**
     * Populates the `_visited` structure with the information read from indexeddb.
     *
     * @private
     */
    async _populateVisited() {
        return this._idb.getAllKeys(this._visitedUITable).then((keys) => {
            if (!this._offline) {
                return; // status changed again meanwhile
            }
            for (const key of keys) {
                const { action, viewType, resId } = JSON.parse(key);
                this._visited[action] = this._visited[action] || { views: {} };
                if (viewType === "form") {
                    this._visited[action].views.form = this._visited[action].views.form || [];
                    this._visited[action].views.form.push(resId);
                } else {
                    this._visited[action].views[viewType] = true;
                }
            }
        });
    }

    /**
     * Disables interactive elements (e.g. buttons) that haven't been tagged as "available-offline".
     *
     * @private
     */
    _offlineUI() {
        // Re-enable elements that have been marked as available offline
        document.querySelectorAll(".o_disabled_offline[data-available-offline]").forEach((el) => {
            el.removeAttribute("disabled");
            el.classList.remove("o_disabled_offline");
        });
        document.querySelectorAll(OfflineManager.SELECTORS_TO_DISABLE.join(", ")).forEach((el) => {
            el.setAttribute("disabled", "");
            el.classList.add("o_disabled_offline");
        });
    }

    /**
     * Re-enables elements that have previously been disabled by @_offlineUI.
     *
     * @private
     */
    _onlineUI() {
        document.querySelectorAll(".o_disabled_offline").forEach((el) => {
            el.removeAttribute("disabled");
            el.classList.remove("o_disabled_offline");
        });
    }

    // -------------------------------------------------------------------------
    // ORM Offline
    // -------------------------------------------------------------------------

    async _syncORM() {
        await navigator.locks.request("db-sync", async () => {
            // Only one tab can execute this block at a time
            await this._updateScheduledORMList();

            for (const [index, { key, value }] of Object.values(this._ormToSync)
                .filter(({ value }) => !value.extras.error)
                .entries()) {
                if (index !== 0) {
                    await new Promise((r) => browser.setTimeout(r, 1000)); // Waits 1 second
                }
                try {
                    await this.orm.call(value.model, value.method, value.args, value.kwargs);
                    this.removeScheduledORM(key);
                } catch {
                    this.scheduleORM(value.model, value.method, value.args, value.kwargs, {
                        id: key,
                        extras: { ...value.extras, error: true },
                    });
                }
            }
        });
    }

    async _updateScheduledORMList() {
        const table = await this._idb.getAllEntries(OfflineManager.ORM_SYNC_TABLE_NAME);
        Object.assign(
            this._ormToSync,
            Object.fromEntries(
                table.map((v) => [v.key, { key: v.key, value: JSON.parse(v.value) }])
            )
        );
    }
}

export const offlineService = {
    dependencies: ["orm"],
    async start(env, services) {
        return new OfflineManager(env, services);
    },
};

registry.category("services").add("offline", offlineService);
