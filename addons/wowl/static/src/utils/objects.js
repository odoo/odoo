/** @odoo-module **/

/**
 * Shallow compares two objects.
 */
export function shallowEqual(obj1, obj2) {
  const obj1Keys = Object.keys(obj1);
  return (
    obj1Keys.length === Object.keys(obj2).length && obj1Keys.every((key) => obj1[key] === obj2[key])
  );
}
