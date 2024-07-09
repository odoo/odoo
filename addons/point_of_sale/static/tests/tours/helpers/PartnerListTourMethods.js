/** @odoo-module */

export function clickPartner(name = "") {
    return {
        content: `click partner '${name}' from partner list screen`,
        trigger: `.partner-list td:contains(${name})`,
        in_modal: true,
    };
}
export function clickPartnerDetails(name) {
    return {
        content: `click partner from partner list screen`,
        trigger: `.partner-list tr:contains("${name}") button.edit-partner-button`,
    };
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

export function checkContactValues(name, address = "", phone = "", mobile = "", email = "") {
    const steps = [
        {
            content: `Check partner "${name}" from partner list screen`,
            trigger: `.partner-list td:contains("${name}")`,
            run: () => {},
        },
        {
            content: `Check address "${address}" for partner "${name}"`,
            trigger: `.partner-list tr:contains("${name}") .partner-line-adress:contains("${address}")`,
            run: () => {},
        },
    ];

    if (phone) {
        steps.push({
            content: `Check phone number "${phone}" for partner "${name}"`,
            trigger: `.partner-list tr:contains("${name}") .partner-line-email:contains("${phone}")`,
            run: () => {},
        });
    }

    if (mobile) {
        steps.push({
            content: `Check mobile number "${mobile}" for partner "${name}"`,
            trigger: `.partner-list tr:contains("${name}") .partner-line-email:contains("${mobile}")`,
            run: () => {},
        });
    }

    if (email) {
        steps.push({
            content: `Check email address "${email}" for partner "${name}"`,
            trigger: `.partner-list tr:contains("${name}") .partner-line-email .email-field:contains("${email}")`,
            run: () => {},
        });
    }

    return steps;
}
