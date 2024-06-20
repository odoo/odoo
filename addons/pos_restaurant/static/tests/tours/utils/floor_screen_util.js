export function table({ name, withClass = "", withoutClass, run = () => {}, numOfSeats }) {
    let trigger = `.floor-map .table${withClass}`;
    if (withoutClass) {
        trigger += `:not(${withoutClass})`;
    }
    if (name) {
        // We use regex to match the exact name
        trigger += `:has(.label:contains(/^${name}$/))`;
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
            content: `right click on floor to open the editing dropdown`,
            trigger: ".floor-selector button.btn-primary",
            run: "rightclick",
        },
        {
            content: `click '${button}' button`,
            trigger: `.dropdown-item:contains("${button}")`,
            run: "click",
        },
    ];
}
export function add(type) {
    return [
        {
            content: `click on the "Add new button"`,
            trigger: `.floor-selector button.fa-plus`,
            run: "click",
        },
        {
            content: `select the New ${type} option`,
            trigger: `.modal-body button:contains("${type}")`,
            in_modal: true,
            run: "click",
        },
    ];
}
export function editTable(name, action) {
    return [
        table({ name, run: "rightclick" }),
        {
            content: `click '${action}' button`,
            trigger: `.dropdown-item:contains("${action}")`,
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
        async run(helpers) {
            await helpers.drag_and_drop(table({ name: parent }).trigger);
        },
    };
}
export function isChildTable(child) {
    return {
        content: `Verify that table ${child} is a child table`,
        trigger: table({ name: child }).trigger + ` .info.opacity-25`,
    };
}
