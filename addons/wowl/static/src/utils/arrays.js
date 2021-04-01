/** @odoo-module **/

/**
 * Helper function returning an extraction handler to use on array elements to
 * return a certain attribute or mutated form of the element.
 *
 * @private
 * @param {string | function} [criterion]
 * @returns {(element: any) => any}
 */
function _getExtractorFrom(criterion) {
  if (criterion) {
    switch (typeof criterion) {
      case "string":
        return (element) => element[criterion];
      case "function":
        return criterion;
      default:
        throw new Error(
          `Expected criterion of type 'string' or 'function' and got '${typeof criterion}'`
        );
    }
  } else {
    return (element) => element;
  }
}

/**
 * Returns an object holding different groups defined by a given criterion
 * or a default one. Each group is a subset of the original given list.
 * The given criterion can either be:
 * - a string: a property name on the list elements which value will be the
 * group name,
 * - a function: a handler that will return the group name from a given
 * element.
 *
 * @param {any[]} array
 * @param {string | function} [criterion]
 * @returns {Object}
 */
export function groupBy(array, criterion) {
  const extract = _getExtractorFrom(criterion);
  const groups = {};
  for (const element of array) {
    const group = String(extract(element));
    if (!(group in groups)) {
      groups[group] = [];
    }
    groups[group].push(element);
  }
  return groups;
}

/**
 * Return a shallow copy of a given array sorted by a given criterion or a default one.
 * The given criterion can either be:
 * - a string: a property name on the array elements returning the sortable primitive
 * - a function: a handler that will return the sortable primitive from a given element.
 * The default order is ascending ('asc'). It can be modified by setting the extra param 'order' to 'desc'.
 *
 * @param {any[]} array
 * @param {string | function} [criterion]
 * @param {"asc" | "desc"} [order="asc"]
 * @returns {any[]}
 */
export function sortBy(array, criterion, order = "asc") {
  const extract = _getExtractorFrom(criterion);
  return array.slice().sort((elA, elB) => {
    const a = extract(elA);
    const b = extract(elB);
    let result;
    if (isNaN(a) && isNaN(b)) {
      result = a > b ? 1 : a < b ? -1 : 0;
    } else {
      result = a - b;
    }
    return order === "asc" ? result : -result;
  });
}
