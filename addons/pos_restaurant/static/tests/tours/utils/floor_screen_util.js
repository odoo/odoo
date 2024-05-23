import { queryOne } from "@odoo/hoot-dom";

export function table({ name, withClass = "", withoutClass, run = () => {}, numOfSeats }) {
    let trigger = `.floor-map .table${withClass}`;
    if (withoutClass) {
        trigger += `:not(${withoutClass})`;
    }
    if (name) {
        trigger += `:has(.label:contains("${name}"))`;
    }
    if (numOfSeats) {
        trigger += `:has(.table-seats:contains("${numOfSeats}"))`;
    }
    return [
        {
            content: `Check table with attributes: ${JSON.stringify(arguments[0])}`,
            trigger,
            run: typeof run === "string" ? run : () => run(trigger),
        },
    ];
}
export const clickTable = (name) => table({ name, run: "click" });
export const hasTable = (name) => table({ name });
export const selectedTableIs = (name) => table({ name, withClass: ".selected" });
export const ctrlClickTable = (name) =>
    table({
        name,
        run: (trigger) => {
            queryOne(trigger).dispatchEvent(
                new MouseEvent("mousedown", { bubbles: true, ctrlKey: true })
            );
        },
    });
export function clickFloor(name) {
    return [
        {
            content: `click '${name}' floor`,
            trigger: `.floor-selector .button-floor:contains("${name}")`,
        },
    ];
}
export function clickEditButton(button) {
    return [
        {
            content: "add table",
            trigger: `.edit-buttons i[aria-label=${button}]`,
        },
    ];
}
export function selectedFloorIs(name) {
    return [
        {
            content: `selected floor is '${name}'`,
            trigger: `.floor-selector .button-floor.btn-primary:contains("${name}")`,
            run: () => {},
        },
    ];
}
export function orderCountSyncedInTableIs(table, count) {
    return [
        {
            trigger: `.floor-map .table .label:contains("${table}") ~ .order-count:contains("${count}")`,
            run: function () {},
        },
    ];
}
export function isShown() {
    return [
        {
            trigger: ".floor-map",
            run: function () {},
        },
    ];
}
