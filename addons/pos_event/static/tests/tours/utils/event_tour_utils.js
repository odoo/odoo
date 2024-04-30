// Part of Odoo. See LICENSE file for full copyright and licensing details.
export function increaseQuantity() {
    return [
        {
            content: `increase quantity`,
            trigger: `.o_event_ticket button:has(i.fa-plus)`,
            in_modal: true,
        },
    ];
}

export function decreaseQuantity() {
    return [
        {
            content: `decrease quantity`,
            trigger: `.o_event_ticket button:has(i.fa-minus)`,
            in_modal: true,
        },
    ];
}

export function pickTicket(name) {
    return [
        {
            content: `pick ticket with name: ${name}`,
            trigger: `.o-event-ticket:contains('${name}')`,
            in_modal: true,
        },
    ];
}

export function printTicket(mode) {
    return [
        {
            content: `print ticket with mode: ${mode}`,
            trigger: `.o-event-button .o-event-${mode}`,
        },
    ];
}

export function eventRemainingSeat(name, seats) {
    return [
        {
            content: `check remaining seats for ${name}`,
            trigger: `article:contains('${name}'):contains('${seats} left')`,
        },
    ];
}
