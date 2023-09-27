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
        // This allows creation of reactive instance by
        // returning reactive `this` in the setup override.
        return this.setup(...arguments);
    }
    /**
     * Create an object with cid. If no cid is in `obj`,
     * cid is computed based on its id. Override `getCID` if you
     * don't want this default calculation of cid.
     * @param {Object?} obj its props copied to this instance.
     */
    setup(obj) {
        return this.setup_base(obj);
    }
    setup_base(obj) {
        obj = obj || {};
        if (!obj.cid) {
            obj.cid = this.getCID(obj);
        }
        Object.assign(this, obj);
        return this;
    }
    /**
     * Default cid getter. Used as local identity of this object.
     * @param {Object} obj
     */
    getCID(obj) {
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
