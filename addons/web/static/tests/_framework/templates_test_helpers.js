import { after } from "@odoo/hoot";
import { registerTemplate as register } from "@web/core/templates";

/**
 * @param {string} name
 * @param {string} templateString
 */
export function registerTemplate(name, templateString) {
    after(register(name, "TEST", `<t>${templateString}</t>`));
}
