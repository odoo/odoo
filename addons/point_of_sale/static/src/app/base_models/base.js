/* @odoo-module */

export class PosCollection extends Array {
    getByCID(cid) {
        return this.find((item) => item.cid == cid);
    }
    add(item) {
        this.push(item);
    }
    remove(item) {
        const index = this.findIndex((_item) => item.cid == _item.cid);
        if (index < 0) {
            return index;
        }
        this.splice(index, 1);
        return index;
    }
    reset() {
        this.length = 0;
    }
    at(index) {
        return this[index];
    }
}

let nextId = 0;

export class PosModel {
    constructor() {
        this.setup(...arguments);
    }
    /**
     * Create an object with cid. If no cid is in the defaultObj,
     * cid is computed based on its id. Override _getCID if you
     * don't want this default calculation of cid.
     * @param {Object?} defaultObj its props copied to this instance.
     */
    setup(defaultObj) {
        this.setup_base(defaultObj);
    }
    setup_base(defaultObj) {
        defaultObj = defaultObj || {};
        if (!defaultObj.cid) {
            defaultObj.cid = this._getCID(defaultObj);
        }
        Object.assign(this, defaultObj);
    }
    /**
     * Default cid getter. Used as local identity of this object.
     * @param {Object} obj
     */
    _getCID(obj) {
        if (obj.id) {
            if (typeof obj.id == "string") {
                return obj.id;
            } else if (typeof obj.id == "number") {
                return `c${obj.id}`;
            }
        }
        return `c${nextId++}`;
    }
}
