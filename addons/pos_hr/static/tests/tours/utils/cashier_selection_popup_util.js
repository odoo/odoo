import { negate } from "@point_of_sale/../tests/generic_helpers/utils";

export function has(item, { subtitleContains, run = () => {} } = {}) {
    const selector = subtitleContains
        ? `.cashier-selection-item:has(:contains("${item}")):has(.employee-subtitle:contains("${subtitleContains}"))`
        : `.cashier-selection-item:contains("${item}")`;

    return [
        {
            content:
                `cashier-selection popup has '${item}'` +
                (subtitleContains ? ` with subtitle containing '${subtitleContains}'` : ""),
            trigger: selector,
            run,
        },
    ];
}

export function hasNot(item, { subtitleContains } = {}) {
    const step = has(item, { subtitleContains })[0];
    return [{ ...step, trigger: negate(step.trigger) }];
}

export function clickMore() {
    return {
        content: "click on 'more' button",
        trigger: ".cashier-selection-item:contains('More...')",
        run: "click",
    };
}
