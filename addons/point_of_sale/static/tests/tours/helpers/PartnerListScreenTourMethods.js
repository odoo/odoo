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

export function clickPartnerDetailsButton(name) {
    return [
        {
            content: `click partner details '${name}' from partner list screen`,
            trigger: `.partner-line:contains('${name}') .edit-partner-button`,
        },
    ];
}

export function clickBack() {
    return [
        {
            trigger: ".partnerlist-screen .button.back",
        },
    ];
}
