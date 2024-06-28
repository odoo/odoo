/** @odoo-module */

export function clickPartner(name = "") {
    return {
        content: `click partner '${name}' from partner list screen`,
        trigger: `.partner-list td:contains("${name}")`,
        in_modal: true,
    };
}
export function clickPartnerDetails(name){
    return {
        content: `click partner from partner list screen`,
        trigger: `.partner-list tr:contains("${name}") button.edit-partner-button`,
    }
}

export function clickBack() {
    return [
        {
            trigger: ".btn-close",
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
