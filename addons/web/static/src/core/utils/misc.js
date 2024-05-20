const eventHandledWeakMap = new WeakMap();
/**
 * Returns whether the given event has been handled with the given markName.
 *
 * @param {Event} ev
 * @param {string} markName
 * @returns {boolean}
 */
export function isEventHandled(ev, markName) {
    if (!eventHandledWeakMap.get(ev)) {
        return false;
    }
    return eventHandledWeakMap.get(ev).includes(markName);
}
/**
 * Marks the given event as handled by the given markName. Useful to allow
 * handlers in the propagation chain to make a decision based on what has
 * already been done.
 *
 * @param {Event} ev
 * @param {string} markName
 */
export function markEventHandled(ev, markName) {
    if (!eventHandledWeakMap.get(ev)) {
        eventHandledWeakMap.set(ev, []);
    }
    eventHandledWeakMap.get(ev).push(markName);
}
/**
 * Typecase values of Element Dataset, it runs on each key and typecast it.
 *
 * @param {Object} dataset
 */
export function typeCastDataset(dataset) {
    const data = {};
    Object.keys(dataset).forEach((key) => {
        const val = +dataset[key];
        if (isNaN(val)) {
            data[key] = dataset[key];
        } else {
            data[key] = val;
        }
    });
    return data;
}
