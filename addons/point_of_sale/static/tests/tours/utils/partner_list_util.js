/** @odoo-module */

export function clickPartner(name = "") {
    return {
        content: `click partner '${name}' from partner list screen`,
        trigger: `.partner-list td:contains(${name})`,
        in_modal: true,
    };
}
