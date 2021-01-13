/** @odoo-module **/
/*
 * Helper function returning an extraction handler to use on array elements to
 * return a certain attribute or mutated form of the element.
 */
function _getExtractorFrom(criterion) {
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
 * @param {any[]} list
 * @param {string | function} [criterion]
 * @returns {Object}
 */
export function groupBy(list, criterion) {
  const extract = _getExtractorFrom(criterion);
  const groups = {};
  for (const element of list) {
    const group = String(extract(element));
    if (!(group in groups)) {
      groups[group] = [];
    }
    groups[group].push(element);
  }
  return groups;
}
