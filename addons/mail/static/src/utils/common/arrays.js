/* @odoo-module */

import { toRaw } from "@odoo/owl";

export function removeFromArray(array, elem) {
    const index = array.indexOf(elem);
    if (index >= 0) {
        array.splice(index, 1);
    }
}

export function removeFromArrayWithPredicate(array, predicate) {
    const index = array.findIndex(predicate);
    if (index >= 0) {
        array.splice(index, 1);
    }
}

/**
 * Replaces the content of array1 with the content of array2. Order of elements
 * is not guaranteed: new elements are inserted last.
 *
 * Smart process to avoid triggering reactives when there is no change between
 * the 2 arrays.
 */
export function replaceArrayWithCompare(array1, array2) {
    array1 = toRaw(array1);
    array2 = toRaw(array2);
    const elementsToRemove = new Set();
    for (const el1 of array1) {
        if (!array2.includes(el1)) {
            elementsToRemove.add(el1);
        }
    }
    for (const el of elementsToRemove) {
        removeFromArray(array1, el);
    }
    for (const el2 of array2) {
        if (!array1.includes(el2)) {
            array1.push(el2);
        }
    }
}
