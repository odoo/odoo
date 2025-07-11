import { negate } from "@point_of_sale/../tests/generic_helpers/utils";

export function has(item, { run = () => {} } = {}) {
    return [
        {
            content: `selection popup has '${item}'`,
            trigger: `.selection-item:contains("${item}")`,
            run,
        },
    ];
}
export function hasNot(item) {
    const step = has(item)[0];
    return [{ ...step, trigger: negate(step.trigger) }];
}
