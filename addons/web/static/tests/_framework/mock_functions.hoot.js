// ! WARNING: this module cannot depend on modules not ending with ".hoot" (except libs) !

import { after } from "@odoo/hoot";

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * @param {string} name
 * @param {OdooModuleFactory} factory
 */
export function mockFunctionsFactory(name, { fn }) {
    return (...args) => {
        function clearMemoizeCaches() {
            for (const cache of memoizeCaches) {
                cache.clear();
            }
        }

        function mockMemoize(func) {
            const cache = new Map();
            memoizeCaches.push(cache);
            const funcName = func.name ? func.name + " (memoized)" : "memoized";
            return {
                [funcName](...args) {
                    if (!cache.size) {
                        after(cache.clear.bind(cache));
                    }
                    if (!cache.has(args[0])) {
                        cache.set(args[0], func(...args));
                    }
                    return cache.get(...args);
                },
            }[funcName];
        }

        const functionsModule = fn(...args);
        const memoizeCaches = [];

        functionsModule.memoize = mockMemoize;
        functionsModule.clearMemoizeCaches = clearMemoizeCaches;

        return functionsModule;
    };
}
