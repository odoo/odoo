/**
 * Polyfill for Map.groupBy (Baseline 2024)
 */
if (!Map.groupBy) {
    Object.defineProperty(Map, "groupBy", {
        configurable: true,
        enumerable: false,
        writable: true,
        value: function (items, callbackfn) {
            const map = new Map();
            let i = 0;
            for (const item of items) {
                const key = callbackfn(item, i++);
                if (map.has(key)) {
                    map.get(key).push(item);
                } else {
                    map.set(key, [item]);
                }
            }
            return map;
        },
    });
}
