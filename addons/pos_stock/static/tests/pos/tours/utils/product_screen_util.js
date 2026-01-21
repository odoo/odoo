import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";

export function clickLotIcon() {
    return [
        {
            content: "click lot icon",
            trigger: ".line-lot-icon",
            run: "click",
        },
    ];
}
export function deleteNthLotNumber(number) {
    return [
        {
            content: "delete lot number",
            trigger: `.lot-container .lot-item:eq(${number - 1}) .btn`,
            run: "click",
        },
    ];
}
export function selectNthLotNumber(number) {
    return [
        {
            trigger: `.o-autocomplete--dropdown-menu .o-autocomplete--dropdown-item:eq(${
                number - 1
            })`,
            run: "click",
        },
        Dialog.confirm(),
    ];
}
export function enterLotNumber(number, tracking = "serial", click = false) {
    const steps = [];
    if (click) {
        steps.push({
            trigger: ".o-autocomplete input",
            run: "click",
        });
    }
    steps.push(
        {
            trigger:
                ".o-autocomplete--dropdown-item a:contains('No existing Lot/Serial number found...')",
        },
        {
            content: "enter lot number",
            trigger: ".o-autocomplete input",
            run: "edit " + number,
        },
        {
            trigger: ".o-autocomplete--dropdown-item a:contains('Create Lot/Serial number...')",
        },
        {
            trigger: ".o-autocomplete input",
            run: "press Enter",
        }
    );
    if (tracking === "serial") {
        steps.push(...serialCheckStep(number));
    }
    steps.push(Dialog.confirm());
    return steps;
}

export function serialCheckStep(number) {
    return [
        {
            content: "Check entered lot/serial number",
            trigger: `.lot-container .lot-item:eq(-1) span:contains(${number})`,
        },
        {
            trigger: ".o-autocomplete input:value()",
        },
    ];
}

export function enterExistingLotNumber(number, tracking = "serial") {
    const steps = [];
    steps.push(
        {
            content: "enter lot number",
            trigger: ".o-autocomplete input",
            run: "edit " + number,
        },
        {
            trigger: ".o-autocomplete input",
            run: "press Enter",
        }
    );
    if (tracking === "serial") {
        steps.push(...serialCheckStep(number));
    }
    steps.push(Dialog.confirm());
    return steps;
}

export function enterLotNumbers(numbers) {
    const steps = [
        {
            trigger: ".o-autocomplete input",
            run: "click",
        },
    ];
    for (const lot of numbers) {
        steps.push(
            {
                content: "enter lot number",
                trigger: ".o-autocomplete input",
                run: "edit " + lot,
            },
            {
                trigger: ".o-autocomplete--dropdown-item a:contains('Create Lot/Serial number...')",
            },
            {
                trigger: ".o-autocomplete input",
                run: "press Enter",
            },
            {
                content: "check entered lot number",
                trigger: `.lot-container .lot-item:eq(-1) span:contains(${lot})`,
            },
            {
                trigger: ".o-autocomplete input:value()",
            }
        );
    }
    steps.push(Dialog.confirm());
    return steps;
}

export function enterExistingLotNumbers(numbers) {
    const steps = [
        {
            trigger: ".o-autocomplete input",
            run: "click",
        },
    ];
    for (const lot of numbers) {
        steps.push(
            {
                content: "enter lot number",
                trigger: ".o-autocomplete input",
                run: "edit " + lot,
            },
            {
                trigger: ".o-autocomplete input",
                run: "press Enter",
            },
            {
                content: "check entered lot number",
                trigger: `.lot-container .lot-item:eq(-1) span:contains(${lot})`,
            },
            {
                trigger: ".o-autocomplete input:value()",
            }
        );
    }
    steps.push(Dialog.confirm());
    return steps;
}

export function checkFirstLotNumber(number) {
    return [
        {
            content: "Check lot number",
            trigger: `.lot-container .lot-item:eq(0) span:contains(${number})`,
        },
    ];
}
