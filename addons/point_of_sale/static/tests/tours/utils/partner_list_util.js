export function clickPartner(name = "", { expectUnloadPage = false } = {}) {
    return {
        content: `click partner '${name}' from partner list screen`,
        trigger: `.modal .partner-list b:contains(${name})`,
        run: "click",
        expectUnloadPage,
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
    };
}

export function checkContactValues(name, address = "", phone = "", mobile = "", email = "") {
    const steps = [
        {
            content: `Check partner "${name}" from partner list screen`,
            trigger: `.partner-list .partner-info:contains("${name}")`,
        },
        {
            content: `Check address "${address}" for partner "${name}"`,
            trigger: `.partner-list .partner-info:contains("${name}") .partner-line-adress:contains("${address}")`,
        },
    ];

    if (phone) {
        steps.push({
            content: `Check phone number "${phone}" for partner "${name}"`,
            trigger: `.partner-list .partner-info:contains("${name}") .partner-line-email:contains("${phone}")`,
        });
    }

    if (mobile) {
        steps.push({
            content: `Check mobile number "${mobile}" for partner "${name}"`,
            trigger: `.partner-list .partner-info:contains("${name}") .partner-line-email:contains("${mobile}")`,
        });
    }

    if (email) {
        steps.push({
            content: `Check email address "${email}" for partner "${name}"`,
            trigger: `.partner-list .partner-info:contains("${name}") .partner-line-email .email-field:contains("${email}")`,
        });
    }

    return steps;
}
export function searchCustomer(val) {
    return [
        {
            isActive: ["mobile"],
            content: `Click search field`,
            trigger: `.fa-search.undefined`,
            run: `click`,
        },
        {
            content: `Search customer with "${val}"`,
            trigger: `.modal-dialog .input-group input`,
            run: `edit ${val}`,
        },
    ];
}
export function searchCustomerValue(val) {
    return [
        ...searchCustomer(val),
        {
            content: `Click on search more if present`,
            trigger: `.search-more-button > button, .partner-list .partner-info:nth-child(1):contains("${val}")`,
            run: function () {
                this.anchor.click();
            },
        },
        {
            content: `Check "${val}" is shown`,
            trigger: `.partner-list .partner-info:nth-child(1):contains("${val}")`,
        },
    ];
}
export function selectFormDiscard() {
    return [
        {
            trigger: "button.o_form_button_cancel",
            content: "Click on discard the customer form",
            run: "click",
        },
    ];
}

export function checkInputForm(fieldName, expectedValue) {
    return [
        {
            trigger: `div[name="${fieldName}"] .o_input`,
            content: `Check if "${expectedValue}" in form div "${fieldName}"`,
            run: function () {
                const input = document.querySelector(`div[name="${fieldName}"] .o_input`);
                if (!input) {
                    console.error(`Element div[name="${fieldName}"] .o_input not found`);
                    return;
                }
                if (input.value !== expectedValue) {
                    console.error(
                        `Validation failed: expected "${expectedValue}", got "${input.value}"`
                    );
                }
            },
        },
    ];
}
