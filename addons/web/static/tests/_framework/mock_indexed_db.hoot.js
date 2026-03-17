// ! WARNING: this module cannot depend on modules not ending with ".hoot" (except libs) !

import { afterEach } from "@odoo/hoot";

/**
 * @param {string} name
 * @param {OdooModuleFactory} factory
 */
export function mockIndexedDBFactory(name, { fn }) {
    return function mockIndexedDB(requireModule, ...args) {
        const indexedDBModule = fn(requireModule, ...args);

        const { IndexedDB } = indexedDBModule;
        let dbs = {};
        afterEach(() => {
            dbs = {};
        });
        class MockedIndexedDB {
            constructor(name) {
                if (!dbs[name]) {
                    dbs[name] = {};
                }
                this.mockIndexedDB = dbs[name];
            }

            async getAllEntries(table) {
                return Object.entries(this.mockIndexedDB[table] || {}).map(([key, value]) => ({
                    key,
                    value,
                }));
            }

            async write(table, key, value) {
                const items = Array.isArray(key) ? key : [{ key, value }];
                if (!(table in this.mockIndexedDB)) {
                    this.mockIndexedDB[table] = {};
                }
                for (const item of items) {
                    this.mockIndexedDB[table][item.key] = item.value;
                }
            }

            async deleteDatabase() {
                this.mockIndexedDB = {};
            }

            async read(table, keys) {
                const results = [];
                for (const key of [].concat(keys)) {
                    results.push({ key, value: this.mockIndexedDB[table]?.[key] });
                }
                if (Array.isArray(keys)) {
                    return results;
                }
                return results[0].value;
            }

            async search(table, searchFcn, count = 8) {
                const targetTable = this.mockIndexedDB[table];
                if (!targetTable) {
                    return [];
                }
                if (!searchFcn) {
                    return Object.entries(dbs[this.name][table] || {})
                        .slice(0, count)
                        .map(([key, value]) => ({
                            key,
                            value,
                        }));
                }
                const results = [];
                for (const [key, value] of Object.entries(targetTable)) {
                    if (await searchFcn(value)) {
                        results.push({ key, value });
                        if (results.length === count) {
                            break;
                        }
                    }
                }
                return results;
            }

            async getAllKeys(table) {
                return Object.keys(this.mockIndexedDB[table] || {});
            }

            async delete(table, key) {
                delete this.mockIndexedDB[table][key];
            }

            async invalidate(matchers = null) {
                if (matchers) {
                    matchers = typeof matchers === "string" ? [matchers] : matchers;

                    const tablesToInvalidate = Object.keys(this.mockIndexedDB).filter((item) =>
                        matchers.some((query) => {
                            if (query instanceof RegExp) {
                                return query.test(item);
                            }
                            return item === query;
                        })
                    );

                    tablesToInvalidate.forEach((table) => (this.mockIndexedDB[table] = {}));
                } else {
                    this.mockIndexedDB = {};
                }
            }
        }

        return Object.assign(indexedDBModule, {
            IndexedDB: MockedIndexedDB,
            _OriginalIndexedDB: IndexedDB,
        });
    };
}
