// Part of Odoo. See LICENSE file for full copyright and licensing details.
export function assertDisabledSlot(slot) {
    return [
        {
            content: `Assert that slot ${slot} is disabled`,
            trigger: `.modal .o_event_slot_btn:disabled:contains('${slot}')`,
        },
    ];
}

export function clickDisplayedSlot(slot) {
    return [
        {
            content: `Select slot ${slot}`,
            trigger: `.modal .o_event_slot_btn:contains('${slot}')`,
            run: "click",
        },
    ];
}
