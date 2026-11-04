/** @odoo-module */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const { EventTarget, indexedDB, Map, String } = globalThis;

const { addEventListener } = EventTarget.prototype;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/** @type {Map<IDBOpenDBRequest, string>} */
const openRequests = new Map();

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export function cleanupIndexedDB() {
    // Deletions are queued by the browser after pending requests on the same
    // database, and before any later "open" on it
    for (const [request, name] of openRequests) {
        if (request.readyState === "done" && !request.transaction) {
            request.result?.close();
        } else {
            // Closing a database while it is opening or upgrading aborts it
            addEventListener.call(request, "success", () => request.result.close());
        }
        indexedDB.deleteDatabase(name);
    }
    openRequests.clear();
}

/**
 * Delegates to the native {@link IDBFactory}, while keeping track of opened
 * databases to close and delete them after each test.
 */
export class MockIDBFactory {
    /** @type {IDBFactory["cmp"]} */
    cmp(first, second) {
        return indexedDB.cmp(first, second);
    }

    /** @type {IDBFactory["databases"]} */
    databases() {
        return indexedDB.databases();
    }

    /** @type {IDBFactory["deleteDatabase"]} */
    deleteDatabase(name) {
        return indexedDB.deleteDatabase(name);
    }

    /** @type {IDBFactory["open"]} */
    open(name, version) {
        const request = indexedDB.open(name, version);
        openRequests.set(request, String(name));
        return request;
    }
}
