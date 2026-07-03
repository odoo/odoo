/**
 * Mirror of `mail/tools/store_handler.py`: the registry that dispatches `/mail/store` fetch params
 * to the registered store handlers, honoring their audience. The registry owns the patchable
 * `handlers` object, and `execute_for_user` resolves the handler by name at call time (patches win).
 */

const AUDIENCES = ["everyone", "internal", "logged_in"];

export class StoreHandlerRegistry {
    constructor() {
        this._items = {};
        this.handlers = {};
    }

    /**
     * @param {string} name fetch param name sent by the client
     * @param {Function} func handler function; its name must start with "store_"
     * @param {{ audience?: "everyone"|"internal"|"logged_in", readonly?: boolean }} [options]
     */
    add(name, func, { audience = "internal", readonly = true } = {}) {
        if (!AUDIENCES.includes(audience)) {
            throw new Error(`Invalid audience "${audience}" for store handler "${name}"`);
        }
        if (this._items[name]) {
            throw new Error(`Store handler "${name}" is already registered`);
        }
        this._validate_func_name(func.name);
        this.handlers[func.name] = func;
        this._items[name] = { audience, func_name: func.name, readonly };
    }

    /**
     * @param {import("@web/../tests/web_test_helpers").MockServer} server
     * @param {import("@mail/../tests/mock_server/store").Store} store
     * @param {Array<string|Array>} fetchParams
     */
    execute_for_user(server, store, fetchParams) {
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = server.env["res.users"];
        const uid = server.env.uid;
        for (const fetchParam of fetchParams) {
            const [name, params, data_id] = StoreHandlerRegistry._parse_fetch_param(fetchParam);
            store.data_id = data_id;
            try {
                const entry = this._items[name];
                if (!entry) {
                    console.warn(`No store handler registered for "${name}"`);
                    continue;
                }
                const has_access =
                    entry.audience === "everyone" ||
                    (entry.audience === "logged_in" && !ResUsers._is_public(uid)) ||
                    (entry.audience === "internal" && ResUsers._is_internal(uid));
                if (!has_access) {
                    console.warn(`User does not have access to store handler "${name}"`);
                    continue;
                }
                const handler = this.handlers[entry.func_name];
                if (params == null) {
                    handler.call(server, store);
                } else if (Array.isArray(params)) {
                    handler.call(server, store, ...params);
                } else {
                    handler.call(server, store, params);
                }
            } finally {
                store.data_id = null;
            }
        }
    }

    isFetchReadonly(fetchParams) {
        // No PG cursor in the mock: kept for parity, not wired into the `/mail/store` route.
        for (const fetchParam of fetchParams) {
            const [name] = StoreHandlerRegistry._parse_fetch_param(fetchParam);
            const entry = this._items[name];
            if (entry && !entry.readonly) {
                return false;
            }
        }
        return true;
    }

    _validate_func_name(func_name) {
        if (!func_name.startsWith("store_")) {
            throw new Error(
                `Store handler function name must start with "store_", got "${func_name}"`
            );
        }
    }

    static _parse_fetch_param(fetchParam) {
        if (typeof fetchParam === "string" || fetchParam instanceof String) {
            return [fetchParam, undefined, undefined];
        }
        return [fetchParam[0], fetchParam[1], fetchParam[2]];
    }
}

export const storeHandlerRegistry = new StoreHandlerRegistry();

/**
 * Register a store handler (the mock equivalent of the `@store_handler(...)` decorator, which does
 * not translate to JS), passing the handler function directly like `registerRoute`. The function
 * must be named and start with "store_"; it lands on the registry's `handlers` object so tests can
 * override it with `patch`/`patchWithCleanup`.
 */
export function registerStoreHandler(name, func, options = {}) {
    storeHandlerRegistry.add(name, func, options);
}
