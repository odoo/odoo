import { afterEach } from "@odoo/hoot";

export function mockIndexedDB(_name, { fn }) {
    return (requireModule, ...args) => {
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

            write(table, key, value) {
                if (!(table in this.mockIndexedDB)) {
                    this.mockIndexedDB[table] = {};
                }
                this.mockIndexedDB[table][key] = value;
            }

            read(table, key) {
                return Promise.resolve(this.mockIndexedDB[table]?.[key]);
            }

            invalidate(tables = null) {
                if (tables) {
                    tables = typeof tables === "string" ? [tables] : tables;
                    for (const table of tables) {
                        if (table in this.mockIndexedDB) {
                            this.mockIndexedDB[table] = {};
                        }
                    }
                } else {
                    this.mockIndexedDB = {};
                }
            }

            cleanUpExpiredEntries() {
                const now = Date.now();
                for (const table in this.mockIndexedDB) {
                    for (const key of Object.keys(this.mockIndexedDB[table])) {
                        const entry = this.mockIndexedDB[table][key];
                        if (entry?.expiresAt && entry.expiresAt < now) {
                            delete this.mockIndexedDB[table][key];
                        }
                    }
                }
            }
        }

        return Object.assign(indexedDBModule, {
            IndexedDB: MockedIndexedDB,
            _OriginalIndexedDB: IndexedDB,
        });
    };
}
