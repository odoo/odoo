export function clickPartner(name = "") {
    return {
        content: `click partner '${name}' from partner list screen`,
        trigger: `.modal .partner-list b:contains(${name})`,
        in_modal: false,
        run: "click",
    };
}
export function clickPartnerOptions(name) {
    return {
        content: `click partner from partner list screen`,
        trigger: `.partner-info:contains("${name}") button.dropdown`,
        run: "click",
    };
}

export function checkDropDownItemText(text) {
    return {
        content: `check for dropdown item containing text`,
        trigger: `.o-dropdown-item:contains("${text}")`,
        in_modal: false,
    };
}

export function checkContactValues(name, address = "", phone = "", mobile = "", email = "") {
    const steps = [
        {
            content: `Check partner "${name}" from partner list screen`,
            trigger: `.partner-list .partner-info:contains("${name}")`,
            run: () => {},
        },
        {
            content: `Check address "${address}" for partner "${name}"`,
            trigger: `.partner-list .partner-info:contains("${name}") .partner-line-adress:contains("${address}")`,
            run: () => {},
        },
    ];

    if (phone) {
        steps.push({
            content: `Check phone number "${phone}" for partner "${name}"`,
            trigger: `.partner-list .partner-info:contains("${name}") .partner-line-email:contains("${phone}")`,
            run: () => {},
        });
    }

    if (mobile) {
        steps.push({
            content: `Check mobile number "${mobile}" for partner "${name}"`,
            trigger: `.partner-list .partner-info:contains("${name}") .partner-line-email:contains("${mobile}")`,
            run: () => {},
        });
    }

    if (email) {
        steps.push({
            content: `Check email address "${email}" for partner "${name}"`,
            trigger: `.partner-list .partner-info:contains("${name}") .partner-line-email .email-field:contains("${email}")`,
            run: () => {},
        });
    }

    return steps;
}

export function searchCustomerValue(val) {
    return [
        {
            isActive: ["mobile"],
            content: `Click search field`,
            trigger: `.fa-search.undefined`,
            run: `click`,
        },
        {
            content: `Search customer with "${val}"`,
            trigger: `.input-group input`,
            run: `edit ${val}`,
        },
        {
            content: `Check "${val}" is shown`,
            trigger: `.partner-list .partner-info:nth-child(1):contains("${val}")`,
            run: () => {},
        },
    ];
}
