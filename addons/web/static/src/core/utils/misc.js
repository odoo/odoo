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
 * Iterate through all parent elements and find the parent where selector
 * matches and return all those parents.
 * This method is similar to parents method of jQuery.
 *
 * @param {HTMLElement} el
 * @param {string} selector
 */
export function parents(el, selector) {
    const parents = [];
    while ((el = el.parentNode) && el !== document) {
      if (!selector || el.matches(selector)) parents.push(el);
    }
    return parents;
}

/**
 * Set height on HTML Element.
 *
 * @param {HTMLElement} el
 * @param {Integer} val
 */
export function setHeight(el, val) {
    if (typeof val === 'function') {
        val = val();
    }
    if (typeof val === 'string') {
        el.style.height = val;
    } else {
        el.style.height = val + 'px';
    }
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
        if(isNaN(val)) {
            data[key] = dataset[key];
        } else {
            data[key] = val;
        }
    });
    return data;
}
