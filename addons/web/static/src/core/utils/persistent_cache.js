import { Deferred } from "@web/core/utils/concurrency";
import { IndexedDB } from "@web/core/utils/indexed_db";

class RamCache {
    constructor() {
        this.ram = {};
    }

    write(table, key, value) {
        if (!(table in this.ram)) {
            this.ram[table] = {};
        }
        this.ram[table][key] = value;
    }

    read(table, key) {
        return this.ram[table]?.[key];
    }

    delete(table, key) {
        delete this.ram[table]?.[key];
    }

    invalidate(table) {
        if (table) {
            if (table in this.ram) {
                this.ram[table] = {};
            }
        } else {
            this.ram = {};
        }
    }
}

export class PersistentCache {
    constructor(name, version) {
        this.indexedDB = new IndexedDB(name, version);
        this.ramCache = new RamCache();
    }

    read(table, key, fallback) {
        const ramValue = this.ramCache.read(table, key);
        if (ramValue) {
            return ramValue;
        }

        const def = new Deferred();
        this.indexedDB.read(table, key).then((result) => {
            if (result) {
                def.resolve(result);
            }
        });
        fallback()
            .then((result) => {
                this.indexedDB.write(table, key, result);
                this.ramCache.write(table, key, Promise.resolve(result));
                def.resolve(result);
                return result;
            })
            .catch((error) => {
                this.ramCache.delete(table, key);
                def.reject(error);
            });
        this.ramCache.write(table, key, def);
        return def;
    }

    invalidate(table) {
        this.indexedDB.invalidate(table);
        this.ramCache.invalidate(table);
    }
}
