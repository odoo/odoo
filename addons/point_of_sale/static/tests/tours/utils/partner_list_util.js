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
