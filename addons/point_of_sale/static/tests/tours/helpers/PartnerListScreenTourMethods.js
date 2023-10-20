/** @odoo-module */

export function clickPartner(name) {
    return [
        {
            content: `click partner '${name}' from partner list screen`,
            trigger: `.partnerlist-screen .partner-list-contents .partner-line td:contains("${name}")`,
        },
    ];
}

export function isShown() {
    return [
        {
            content: "partner list screen is shown",
            trigger: ".pos-content .partnerlist-screen",
            run: () => {},
        },
    ];
}
