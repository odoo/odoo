/** @odoo-module **/

/**
 * This file contains various utility functions that do not have a well defined
 * category.
 */

// -----------------------------------------------------------------------------

/**
 * @returns {boolean} true for the browser base on Chromium (Google Chrome, Opera, Edge)
 */
export function isBrowserChromium() {
  return navigator.userAgent.includes("Chrome");
}

// -----------------------------------------------------------------------------

/**
 * Returns a function, that, as long as it continues to be invoked, will not
 * be triggered. The function will be called after it stops being called for
 * N milliseconds. If `immediate` is passed, trigger the function on the
 * leading edge, instead of the trailing.
 *
 * Inspired by https://davidwalsh.name/javascript-debounce-function
 * @param {Function} func
 * @param {number} wait
 * @param {boolean} immediate
 * @returns {Function}
 */
export function debounce(func, wait, immediate) {
  let timeout;
  return function () {
    const context = this;
    const args = arguments;
    function later() {
      if (!immediate) {
        func.apply(context, args);
      }
    }
    const callNow = immediate && !timeout;
    odoo.browser.clearTimeout(timeout);
    timeout = odoo.browser.setTimeout(later, wait);
    if (callNow) {
      func.apply(context, args);
    }
  };
}

// -----------------------------------------------------------------------------

/**
 * For debugging purpose, this function will convert a json node back to xml
 *
 * @param {Object} node
 * @param {boolean} [humanReadable]
 * @param {number} [indent]
 * @returns {string} the XML representation of the JSON node
 */
export function json_node_to_xml(node, humanReadable, indent) {
  indent = indent || 0;
  const sindent = humanReadable ? new Array(indent + 1).join("\t") : "";
  let r = sindent + "<" + node.tag;
  const cr = humanReadable ? "\n" : "";
  if (typeof node === "string") {
    return (
      sindent +
      node
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
    );
  } else if (
    typeof node.tag !== "string" ||
    !node.children instanceof Array ||
    !node.attrs instanceof Object
  ) {
    throw new Error(`Node [${JSON.stringify(node)}] is not a JSONified XML node`);
  }
  for (const attr in node.attrs) {
    let vattr = node.attrs[attr];
    if (typeof vattr !== "string") {
      // domains, ...
      vattr = JSON.stringify(vattr);
    }
    vattr = vattr
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
    if (humanReadable) {
      vattr = vattr.replace(/&quot;/g, "'");
    }
    r += " " + attr + '="' + vattr + '"';
  }
  if (node.children && node.children.length) {
    r += ">" + cr;
    const childs = [];
    for (let i = 0, ii = node.children.length; i < ii; i++) {
      childs.push(json_node_to_xml(node.children[i], humanReadable, indent + 1));
    }
    r += childs.join(cr);
    r += cr + sindent + "</" + node.tag + ">";
    return r;
  } else {
    return r + "/>";
  }
}
