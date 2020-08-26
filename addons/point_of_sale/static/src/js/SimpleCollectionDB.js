odoo.define('point_of_sale.SimpleCollectionDB', function (require) {
    'use strict';

    class SimpleCollectionDB {
        constructor(prefixGetter, name) {
            this.name = name;
            this.prefixGetter = prefixGetter;
            this.keyForKeys = `${this.prefixGetter()}-${this.name}-item-keys`;
        }
        _getRealKey(key) {
            return `${this.prefixGetter()}-${this.name}-${key}`;
        }
        getKeys() {
            return JSON.parse(localStorage.getItem(this.keyForKeys)) || [];
        }
        getItems() {
            return this.getKeys().map((key) => this.getItem(key)) || [];
        }
        getItem(key) {
            const realKey = this._getRealKey(key);
            return JSON.parse(localStorage.getItem(realKey));
        }
        setItem(key, item) {
            const realKey = this._getRealKey(key);
            const keySet = new Set(this.getKeys());
            keySet.add(key);
            localStorage.setItem(this.keyForKeys, JSON.stringify([...keySet]));
            localStorage.setItem(realKey, JSON.stringify(item));
        }
        removeItem(key) {
            const realKey = this._getRealKey(key);
            const keySet = new Set(this.getKeys());
            keySet.delete(key);
            localStorage.setItem(this.keyForKeys, JSON.stringify([...keySet]));
            localStorage.removeItem(realKey);
        }
        clearItems() {
            const keys = this.getKeys();
            for (const key of keys) {
                const realKey = this._getRealKey(key);
                localStorage.removeItem(realKey);
            }
            localStorage.removeItem(this.keyForKeys);
        }
    }

    return SimpleCollectionDB;
});
