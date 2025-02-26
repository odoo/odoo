import { markup } from "@odoo/owl";

import { Markup } from "@web/core/utils/html";
import { patch } from "@web/core/utils/patch";

/** @type {Markup} */
const markupStaticPatch = {
    /**
     * Safely creates a Document fragment from content. If content was flagged as safe HTML using
     * `markup()` it is parsed as HTML. Otherwise it is escaped and parsed as text.
     *
     * @param {string|ReturnType<markup>} content
     */
    createDocumentFragmentFromContent(content) {
        return new document.defaultView.DOMParser().parseFromString(
            Markup.escape(content),
            "text/html"
        );
    },
    /**
     * Applies string replace on content and returns a markup result built for HTML.
     *
     * @param {string|ReturnType<markup>} content
     * @param {string | RegExp} search
     * @param {string} replacement
     * @returns {ReturnType<markup>}
     */
    replace(content, search, replacement) {
        content = Markup.escape(content);
        if (typeof search === "string" || search instanceof String) {
            search = Markup.escape(search);
        }
        replacement = Markup.escape(replacement);
        return markup(content.replace(search, replacement));
    },
    /**
     * Applies string replaceAll on content and returns a markup result built for HTML.
     *
     * @param {string|ReturnType<markup>} content
     * @param {string | RegExp} search
     * @param {string} replacement
     * @returns {ReturnType<markup>}
     */
    replaceAll(content, search, replacement) {
        content = Markup.escape(content);
        if (typeof search === "string" || search instanceof String) {
            search = Markup.escape(search);
        }
        replacement = Markup.escape(replacement);
        return markup(content.replaceAll(search, replacement));
    },
    /**
     * Applies string trim on content and returns a markup result built for HTML.
     *
     * @param {string|ReturnType<markup>} content
     * @returns {string|ReturnType<markup>}
     */
    trim(content) {
        content = Markup.escape(content);
        return markup(content.trim());
    },
};
patch(Markup, markupStaticPatch);
