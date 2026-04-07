import { IndexedDB } from "@web/core/utils/indexed_db";

export class IndexDBEntry {
    /** @type {string} */
    key;
    /** @type {string} */
    table;
    _db;
    constructor(table, key) {
        this._db = new IndexedDB("mail");
        this.table = table;
        this.key = key;
    }
    async get() {
        return await this._db.read(this.table, this.key);
    }
    async set(value) {
        await this._db.write(this.table, this.key, value);
    }
    async remove() {
        await this._db.delete(this.table, this.key);
    }
}
