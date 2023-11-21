/** @odoo-module */

import { App } from "@odoo/owl";

/**
 * Registers the given template without parsing it in the global `templates`
 * object. Registered template is also added to each existing Owl App.
 *
 * @param {string} name Name of the template
 * @param {string} templateString Template string
 */

export function registerTemplate(name, templateString) {
    templates[name] = templateString;
    for (const app of App.apps) {
        app.addTemplate(name, templateString);
    }
}

/**
 * Object containing all the Owl templates that have been loaded.
 * This can be imported by the modules in order to use it when instantiating a
 * new App.
 */
export const templates = {};
