odoo.define('mail/static/src/model/model_recordset.js', function (require) {
'use strict';

class RecordSet {

    /**
     * @param {Model[]} [records=[]] iterable of records
     */
    constructor(records = []) {
        this._records = new Set(records);
    }

    [Symbol.iterator]() {
        return this._records[Symbol.iterator]();
    }

    concat(records) {
        return new RecordSet([...this._records, ...records]);
    }

    filter(...args) {
        return new RecordSet([...this._records].filter(...args));
    }

    find(predicate) {
        for (const record of this._records) {
            if (predicate(record)) {
                return record;
            }
        }
        return undefined;
    }

    forEach(...args) {
        this._records.forEach(...args);
    }

    has(record) {
        return this._records.has(record);
    }

    includes(record) {
        return this.has(record);
    }

    last() {
        const {
            length: l,
            [l - 1]: last,
        } = [...this._records];
        return last;
    }

    get length() {
        return this._records.size;
    }

    map(...args) {
        return [...this._records].map(...args);
    }

    reduce(...args) {
        return [...this._records].reduce(...args);
    }

    some(predicate) {
        for (const record of this._records) {
            if (predicate(record)) {
                return true;
            }
        }
        return false;
    }

    sort(...args) {
        return new RecordSet([...this._records].sort(...args));
    }
}

return {
    RecordSet,
};

});
