/** @odoo-module */

import { App } from "@odoo/owl";

const parser = new DOMParser();

/**
 * Parses an XML template string and registers the [t-name] elements in the global
 * `templates` element. Registered templates are also added to each existing Owl App.
 *
 * @param {string} moduleName
 * @param {string} templateString
 */
export function registerTemplate(moduleName, templateString) {
    const doc = parser.parseFromString(templateString, "text/xml");
    if (doc.querySelector("parsererror")) {
        // The generated error XML is non-standard so we log the full content to
        // ensure that the relevant info is actually logged.
        let strError = "";
        const nodes = doc.querySelectorAll("parsererror");
        for (const node of nodes) {
            strError += node.textContent.trim() + "\n";
        }
        throw new Error(strError);
    }

    templates.documentElement.append(...doc.querySelectorAll("templates > [t-name]"));

    for (const app of App.apps) {
        app.addTemplates(templates, app);
    }
}

/**
 * XML element containing all the Owl templates that have been loaded.
 * This can be imported by the modules in order to use it when instantiating a
 * new App.
 */
export const templates = parser.parseFromString("<odoo/>", "text/xml");
