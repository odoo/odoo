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
    return {
        content: `Check table with attributes: ${JSON.stringify(arguments[0])}`,
        trigger,
        run: typeof run === "string" ? run : () => run(trigger),
    };
}
export const clickTable = (name) => table({ name, run: "click" });
export const hasTable = (name) => table({ name });
export const selectedTableIs = (name) => table({ name, withClass: ".selected" });
export const ctrlClickTable = (name) =>
    table({
        name,
        run: (trigger) => {
            queryOne(trigger).dispatchEvent(
                new MouseEvent("click", { bubbles: true, ctrlKey: true })
            );
        },
    });
export function clickFloor(name) {
    return [
        {
            content: `click '${name}' floor`,
            trigger: `.floor-selector .button-floor:contains("${name}")`,
            run: "click",
        },
    ];
}
export function clickEditButton(button) {
    return [
        {
            content: "add table",
            trigger: `.edit-buttons i[aria-label=${button}]`,
            run: "click",
        },
    ];
}
export function selectedFloorIs(name) {
    return [
        {
            content: `selected floor is '${name}'`,
            trigger: `.floor-selector .button-floor.btn-primary:contains("${name}")`,
        },
    ];
}
export function orderCountSyncedInTableIs(table, count) {
    return [
        {
            trigger: `.floor-map .table .label:contains("${table}") ~ .order-count:contains("${count}")`,
        },
    ];
}
export function isShown() {
    return [
        {
            trigger: ".floor-map",
        },
    ];
}
export function linkTables(child, parent) {
    return {
        content: `Drag table ${child} onto table ${parent} in order to link them`,
        trigger: table({ name: child }).trigger,
        run: `drag_and_drop(${table({ name: parent }).trigger})`,
    };
}
export function isChildTable(child) {
    return {
        content: `Verify that table ${child} is a child table`,
        trigger: table({ name: child }).trigger + ` .info.opacity-25`,
    };
}
