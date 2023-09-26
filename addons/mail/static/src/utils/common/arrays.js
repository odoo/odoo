/* @odoo-module */

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
