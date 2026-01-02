import { negateStep } from "@point_of_sale/../tests/generic_helpers/utils";

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

export function clickDropDownItemText(text) {
    return {
        content: `click for dropdown item containing text`,
        trigger: `.o-dropdown-item:contains("${text}")`,
        run: "click",
    };
}

export function clickSettleOrderName(
    prefix,
    suffix = "",
    checkCurrentYear = false,
    availability = true
) {
    let trigger = `tr.o_data_row td[name='name']:contains("${prefix}")`;
    if (checkCurrentYear) {
        trigger += `:contains("${new Date().getFullYear()}")`;
    }
    if (suffix) {
        trigger += `:contains("${suffix}")`;
    }
    const step = {
        content: "Check the settle due account line is present",
        trigger,
        run: "click",
    };
    if (!availability) {
        return negateStep(step);
    }
    return step;
}

export function settleCustomerAccount(
    partner,
    dueAmount,
    orderPrefix,
    orderSuffix = "",
    checkYear = false,
    orderSettlement = false,
    availability = true
) {
    const steps = [
        {
            trigger: `tr:contains(${partner}) .partner-due:contains(${dueAmount})`,
        },
        clickPartnerOptions(`${partner}`),
    ];
    const buttonText = orderSettlement ? "Settle orders" : "Settle invoices";
    steps.push(
        ...[
            clickDropDownItemText(buttonText),
            clickSettleOrderName(orderPrefix, orderSuffix, checkYear, availability),
        ]
    );
    return steps;
}

export function checkContactValues(name, address = "", phone = "", email = "") {
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

    if (email) {
        steps.push({
            content: `Check email address "${email}" for partner "${name}"`,
            trigger: `.partner-list .partner-info:contains("${name}") .partner-line-email .email-field:contains("${email}")`,
        });
    }

    return steps;
}

export function checkCustomerShown(val) {
    return {
        content: `Check "${val}" is shown`,
        trigger: `.partner-list .partner-info:nth-child(1):contains("${val}")`,
    };
}

export function searchCustomerValue(val, pressEnter = false) {
    const steps = [
        {
            isActive: ["mobile"],
            content: `Click search field`,
            trigger: `.modal-dialog .fa-search.undefined`,
            run: `click`,
        },
        {
            content: `Search customer with "${val}"`,
            trigger: `.modal-dialog .input-group input`,
            run: `edit ${val}`,
        },
    ];

    if (pressEnter) {
        steps.push({
            content: `Manually trigger keyup event`,
            trigger: ".modal-header .input-group input",
            run: function () {
                document
                    .querySelector(".modal-header .input-group input")
                    .dispatchEvent(new KeyboardEvent("keyup", { key: "" }));
            },
        });
        steps.push({
            content: `Press Enter to trigger "search more"`,
            trigger: `.modal-dialog .input-group input`,
            run: function () {
                document
                    .querySelector(".modal-dialog .input-group input")
                    .dispatchEvent(new KeyboardEvent("keydown", { bubbles: true, key: "Enter" }));
            },
        });
    }
    steps.push(checkCustomerShown(val));
    return steps;
}

export function scrollBottom() {
    return {
        content: `Scroll to the bottom of the partner list`,
        trigger: `.modal-body.partner-list`,
        run: () => {
            const partnerList = document.querySelector(".modal-body.partner-list");
            partnerList.scrollTop = partnerList.scrollHeight;
        },
    };
}

export function isShown() {
    return [
        {
            content: "partner list screen is shown",
            trigger: ".modal .partner-list",
        },
    ];
}
