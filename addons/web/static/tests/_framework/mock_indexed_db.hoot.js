// ! WARNING: this module cannot depend on modules not ending with ".hoot" (except libs) !

import { afterEach } from "@odoo/hoot";

class Mutex {
    constructor() {
        this.queue = Promise.resolve();
    }

    exec(task) {
        this.queue = this.queue.then(() => task()).catch(() => {});
        return this.queue;
    }
}

/**
 * @param {string} name
 * @param {OdooModuleFactory} factory
 */
export function mockIndexedDBFactory(name, { fn }) {
    return function mockIndexedDB(requireModule, ...args) {
        const indexedDBModule = fn(requireModule, ...args);

        const { IndexedDB, VERSION_TABLE, VERSION_KEY } = indexedDBModule;
        let dbs = {};
        afterEach(() => {
            dbs = {};
        });
        class MockedIndexedDB {
            constructor(name, version) {
                if (!dbs[name]) {
                    dbs[name] = {};
                }
                this.name = name;
                this.mutex = new Mutex();
                this.mutex.exec(() => this._checkVersion(version));
            }

            get objectStoreNames() {
                return Object.keys(dbs[this.name]);
            }

            // Used in the test to explore the DB!
            get mockIndexedDB() {
                return dbs[this.name];
            }

            _checkVersion(version) {
                const currentVersion = dbs[this.name][VERSION_TABLE]?.[VERSION_KEY];
                if (!currentVersion) {
                    dbs[this.name][VERSION_TABLE] = { [VERSION_KEY]: version };
                } else if (currentVersion !== version) {
                    dbs[this.name] = { [VERSION_TABLE]: { [VERSION_KEY]: version } };
                }
            }

            async getAllEntries(table) {
                return this.mutex.exec(() =>
                    Object.entries(dbs[this.name][table] || {}).map(([key, value]) => ({
                        key,
                        value,
                    }))
                );
            }

            async write(table, key, value) {
                return this.mutex.exec(() => {
                    const items = Array.isArray(key) ? key : [{ key, value }];
                    if (!(table in dbs[this.name])) {
                        dbs[this.name][table] = {};
                    }
                    for (const item of items) {
                        dbs[this.name][table][item.key] = item.value;
                    }
                });
            }

            async deleteDatabase() {
                return this.mutex.exec(() => (dbs[this.name] = {}));
            }

            async read(table, keys) {
                return this.mutex.exec(() => {
                    const results = [];
                    for (const key of [].concat(keys)) {
                        results.push({ key, value: dbs[this.name][table]?.[key] });
                    }
                    if (Array.isArray(keys)) {
                        return results;
                    }
                    return results[0].value;
                });
            }

            async search(table, searchFcn, count = 8) {
                return this.mutex.exec(async () => {
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
                });
            }

            async getAllKeys(table) {
                return this.mutex.exec(() => Object.keys(dbs[this.name][table] || {}));
            }

            async delete(table, key) {
                return this.mutex.exec(() => delete dbs[this.name][table][key]);
            }

            async invalidate(matchers = null) {
                return this.mutex.exec(() => {
                    const existingTableNames = this.objectStoreNames.filter(
                        (table) => table !== VERSION_TABLE
                    );
                    let tablesToInvalidate = [];
                    if (matchers && matchers.length) {
                        matchers = typeof matchers === "string" ? [matchers] : matchers;

                        tablesToInvalidate = existingTableNames.filter((item) =>
                            matchers.some((query) => {
                                if (query instanceof RegExp) {
                                    return query.test(item);
                                }
                                return item === query;
                            })
                        );
                    } else {
                        tablesToInvalidate = existingTableNames;
                    }
                    if (tablesToInvalidate.length) {
                        tablesToInvalidate.forEach((table) => (dbs[this.name][table] = {}));
                    }
                });
            }
        }

        return Object.assign(indexedDBModule, {
            IndexedDB: MockedIndexedDB,
            _OriginalIndexedDB: IndexedDB,
        });
    };
}
