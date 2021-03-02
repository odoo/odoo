/** @odoo-module **/

/**
 * Escapes a string to use as a RegExp.
 * @url https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Regular_Expressions#Escaping
 *
 * @param {string} str
 * @returns {string} escaped string to use as a RegExp
 */
export function escapeRegExp(str) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * Intersperses ``separator`` in ``str`` at the positions indicated by
 * ``indices``.
 *
 * ``indices`` is an array of relative offsets (from the previous insertion
 * position, starting from the end of the string) at which to insert
 * ``separator``.
 *
 * There are two special values:
 *
 * ``-1``
 *   indicates the insertion should end now
 * ``0``
 *   indicates that the previous section pattern should be repeated (until all
 *   of ``str`` is consumed)
 *
 * @param {string} str
 * @param {number[]} indices
 * @param {string} separator
 * @returns {string}
 */
export function intersperse(str, indices, separator = "") {
  separator = separator || "";
  const result = [];
  let last = str.length;
  for (let i = 0; i < indices.length; ++i) {
    let section = indices[i];
    if (section === -1 || last <= 0) {
      // Done with string, or -1 (stops formatting string)
      break;
    } else if (section === 0 && i === 0) {
      // repeats previous section, which there is none => stop
      break;
    } else if (section === 0) {
      // repeat previous section forever
      //noinspection AssignmentToForLoopParameterJS
      section = indices[--i];
    }
    result.push(str.substring(last - section, last));
    last -= section;
  }
  const s = str.substring(0, last);
  if (s) {
    result.push(s);
  }
  return result.reverse().join(separator);
}

/**
 * Returns a string formatted using given values.
 * If the value is an object, its keys will replace `%(key)s` expressions.
 * If the values are a set of strings, they will replace `%s` expressions.
 * If no value is given, the string will not be formatted.
 *
 * @param {string} s
 * @param {...string} ...values
 * @returns {string}
 */
export function sprintf(s, ...values) {
  if (values.length === 1 && typeof values[0] === "object") {
    const valuesDict = values[0];
    s = s.replace(/\%\(?([^\)]+)\)s/g, (match, value) => valuesDict[value]);
  } else if (values.length > 0) {
    s = s.replace(/\%s/g, () => values.shift());
  }
  return s;
}

/**
 * Capitalizes a string: "abc def" => "Abc def"
 *
 * @param {string} s the input string
 * @returns {string}
 */
export function capitalize(s) {
  return s ? s[0].toUpperCase() + s.slice(1) : "";
}
