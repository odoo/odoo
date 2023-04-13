/** @odoo-module */

import { useEffect, useState } from "@odoo/owl";

/**
 * This hook returns the target detected by the intersection observer.
 * @param {ref} root : reference to the element that is the root of the intersection observer
 * @param {Object} targets : object with references to each target
 * @param {()=>{[boolean]}} getDeps : function that returns a list with one item; this item should be true when the effect should be run and false when it should be stopped
 * @param {*} callback : function that is called when the tag is detected
 * @returns {{name:string}} : object with the name of the tag that is currently selected
 */
export function useDetection(root, targets, getDeps, callback = () => {}) {
    const detected = useState({ name: "" });
    useEffect((stop) => {
        if (stop) {
            return;
        }
        /** @type{IntersectionObserverEntry[]} */
        let entriesOnScreen = [];
        const observer = new IntersectionObserver(
            (entries) => {
                entriesOnScreen = updateEntries(entriesOnScreen, entries);
                detected.name = getName(getFirst(entriesOnScreen));
                callback(detected.name);
            },
            {
                root: root.el,
                rootMargin: "-100px",
            }
        );
        Object.keys(targets).forEach((tag) => {
            observer.observe(targets[tag]?.el);
        });
        return () => {
            observer.disconnect();
        };
    }, getDeps);

    return detected;
}
/**
 * @param {IntersectionObserverEntry[]} entries
 * @returns {IntersectionObserverEntry} : the entry that is the highest on the page
 */
function getFirst(entries) {
    return getMax(entries, (entry) => entry.target.offsetTop);
}

/**
 * @template T
 * @param {T[]} entries - The array of objects to search through.
 * @param {Function} [criterion=(x) => x] - A function that returns a number for each entry. The entry with the highest value of this function will be returned. If not provided, defaults to an identity function that returns the entry itself.
 * @param {boolean} [inverted=false] - If true, the entry with the lowest value of the criterion function will be returned instead.
 * @returns {T} The entry with the highest or lowest value of the criterion function, depending on the value of `inverted`.
 */
function getMax(entries, criterion = (x) => x, inverted = false) {
    return entries.reduce((prev, current) => {
        const res = criterion(prev) < criterion(current);
        return (inverted ? !res : res) ? prev : current;
    });
}

/**
 * @param {IntersectionObserverEntry[]} entriesOnScreen
 * @param {IntersectionObserverEntry[]} entries
 * @returns {IntersectionObserverEntry[]}
 */
function updateEntries(entriesOnScreen, entries) {
    const entriesNoLongerIntersecting = entries.filter((entry) => !entry.isIntersecting);
    const newEntriesIntersecting = entries.filter((entry) => entry.isIntersecting);
    return [
        ...entriesOnScreen.filter((entry) => notIncludes(entry, entriesNoLongerIntersecting)),
        ...newEntriesIntersecting.filter((entry) => notIncludes(entry, entriesOnScreen)),
    ];
}

/**
 * @param {IntersectionObserverEntry} entry
 * @param {IntersectionObserverEntry[]} entries
 * @returns {boolean}
 */
function notIncludes(entry, entries) {
    return !entries.some((e) => getName(e) === getName(entry));
}

/**
 * @param {IntersectionObserverEntry} item
 * @returns {string}: the title of the group
 */
function getName(item) {
    return item.target.querySelector("h3").textContent;
}
