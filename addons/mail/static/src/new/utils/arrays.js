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

export function replaceArrayWithCompare(array1, array2, compareFn) {
    for (const el1 of array1) {
        if (!array2.some((el2) => compareFn(el1, el2))) {
            removeFromArrayWithPredicate(array1, (el) => compareFn(el, el1));
        }
    }
    for (const el2 of array2) {
        if (!array1.some((el1) => compareFn(el1, el2))) {
            array1.push(el2);
        }
    }
}
