// @odoo-module ignore
if (!Object.hasOwn) {
    Object.hasOwn = (obj, key) => Object.prototype.hasOwnProperty.call(obj, key);
}

/**
 * Polyfill for Object.groupBy (Baseline 2024)
 */
if (!Object.groupBy) {
    Object.defineProperty(Object, "groupBy", {
        configurable: true,
        enumerable: false,
        writable: true,
        value: function (items, callbackfn) {
            const obj = Object.create(null);
            let i = 0;
            for (const item of items) {
                const key = callbackfn(item, i++);
                if (obj[key]) {
                    obj[key].push(item);
                } else {
                    obj[key] = [item];
                }
            }
            return obj;
        },
    });
}
