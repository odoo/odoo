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

            async write(table, key, value) {
                if (!(table in this.mockIndexedDB)) {
                    this.mockIndexedDB[table] = {};
                }
                this.mockIndexedDB[table][key] = value;
            }

            async read(table, key) {
                return this.mockIndexedDB[table]?.[key];
            }

            async invalidate(tables = null) {
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
        }

        return Object.assign(indexedDBModule, {
            IndexedDB: MockedIndexedDB,
            _OriginalIndexedDB: IndexedDB,
        });
    };
}
