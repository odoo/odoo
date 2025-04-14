export function mockIndexedDB(_name, { fn }) {
    return (requireModule, ...args) => {
        const indexedDBModule = fn(requireModule, ...args);

        const { IndexedDB } = indexedDBModule;
        class MockedIndexedDB {
            constructor() {
                this.mockIndexedDB = {};
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

            invalidate(table) {
                if (table) {
                    if (table in this.mockIndexedDB) {
                        this.mockIndexedDB[table] = {};
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
