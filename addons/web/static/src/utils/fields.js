/** @odoo-module **/

/**
 * Returns a string representing an many2one.  If the value is false, then we
 * return an empty string.  Note that it accepts two types of input parameters:
 * an array, in that case we assume that the many2one value is of the form
 * [id, nameget], and we return the nameget, or it can be an object, and in that
 * case, we assume that it is a record datapoint from a BasicModel.
 *
 * @param {Array|Object|false} value
 * @param {Object} [field]
 *        a description of the field (note: this parameter is ignored)
 * @param {{escape?: boolean}} [options] additional options
 * @param {boolean} [options.escape=false] if true, escapes the formatted value
 * @returns {string}
 */
export function formatMany2one(value, field, options) {
  if (!value) {
    value = "";
  } else if (Array.isArray(value)) {
    // value is a pair [id, nameget]
    value = value[1];
  } else {
    // value is a datapoint, so we read its display_name field, which
    // may in turn be a datapoint (if the name field is a many2one)
    while (value.data) {
      value = value.data.display_name || "";
    }
  }
  if (options && options.escape) {
    value = encodeURIComponent(value);
  }
  return value;
}
