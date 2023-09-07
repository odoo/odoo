/** @odoo-module **/

/**
 * Utils
 *
 * Various generic utility functions
 */

import { escape, escapeMethod } from "@web/core/utils/strings";

// notable issues:
// * objects can't be negative in JS, so !!"" -> false but
//   !!(new String) -> true, likewise markup
// TODO (?)
// * Markup.join / Markup#join => escapes items and returns a Markup
// * Markup#replace => automatically escapes the replacements (difficult impl)

// get a reference to the internalMarkup class from owl
const _Markup = owl.markup('').constructor;
_Markup.prototype[escapeMethod] = function () {
    return this;
}

/**
 * Returns a markup object, which acts like a String but is considered safe by
 * `escape`, and will therefore be injected as-is (without additional
 * escaping) in templates. Can be used to inject dynamic HTML in templates
 * (where the template itself can't), see first example.
 *
 * Can also be used as a *template tag*, in which case the literal content
 * won't be escaped but the substitutions which are not already markup objects
 * will be.
 *
 * ## WARNINGS:
 * * A markup object is a `String` (boxed) but not a `string` (primitive), they
 *   typecheck differently which can be relevant.
 * * To strip out the "markupness", just call `String(markup)`.
 * * Most string operations (e.g. concatenation, `String#replace`, ...) will
 *   also strip out markupness
 * * If the input is empty, returns a regular string (that way boolean tests
 *   work as expected).
 *
 * @returns a markup object
 *
 * @example regular function
 * let h;
 * if (someTest) {
 *     h = Markup(_t("This is a <strong>success</strong>"));
 * } else {
 *     h = Markup(_t("Things did <strong>not</strong> work out"));
 * }
 * qweb.render("some_template", { message: h });
 *
 * @example template tag
 * const escaped = "<some> text";
 * const asis = Markup`some <b>text</b>`;
 * const h = Markup`Regular strings get ${escaped} but markup is injected ${asis}`;
 */
export function Markup(v, ...exprs) {
    if (!(v instanceof Array)) {
        return v ? new _Markup(v) : '';
    }
    const elements = [];
    let i = 0;
    for(; i < exprs.length; ++i) {
        elements.push(v[i], escape(exprs[i]));
    }
    elements.push(v[i]);

    const s = elements.join('');
    if (!s) { return '' }
    return new _Markup(s);
}

const utils = {
    Markup,
};

export default utils;
