/** @odoo-module */

export function clickTable(name) {
    return [
        {
            content: `click table '${name}'`,
            trigger: `.floor-map .table .label:contains("${name}")`,
        },
    ];
}
export function clickFloor(name) {
    return [
        {
            content: `click '${name}' floor`,
            trigger: `.floor-selector .button-floor:contains("${name}")`,
        },
    ];
}
export function clickEdit() {
    return [
        {
            content: "Click Menu button",
            trigger: ".menu-button",
        },
        {
            content: `click edit button`,
            trigger: `.edit-button`,
        },
    ];
}
export function clickAddTable() {
    return [
        {
            content: "add table",
            trigger: `.edit-button i[aria-label=Add]`,
        },
    ];
}
export function clickDuplicate() {
    return [
        {
            content: "duplicate table",
            trigger: `.edit-button i[aria-label=Copy]`,
        },
    ];
}
export function clickRename() {
    return [
        {
            content: "rename table",
            trigger: `.edit-button i[aria-label=Rename]`,
        },
    ];
}
export function clickSeats() {
    return [
        {
            content: "change number of seats",
            trigger: `.edit-button i[aria-label=Seats]`,
        },
    ];
}
export function clickTrash() {
    return [
        {
            content: "trash table",
            trigger: `.edit-button.trash`,
        },
    ];
}
export function closeEdit() {
    return [
        {
            content: "Close edit mode",
            trigger: ".edit-button .close-edit-button",
        },
    ];
}
export function changeShapeTo(shape) {
    return [
        {
            content: `change shape to '${shape}'`,
            trigger: `.edit-button.button-option${shape === "round" ? ".round" : ".square"}`,
        },
    ];
}
export function ctrlClickTable(name) {
    return [
        {
            content: `ctrl click table '${name}'`,
            trigger: `.floor-map .table .label:contains("${name}")`,
            run: () => {
                $(`.floor-map .table .label:contains("${name}")`)[0].dispatchEvent(
                    new MouseEvent("click", { bubbles: true, ctrlKey: true })
                );
            },
        },
    ];
}
export function backToFloor() {
    return [
        {
            content: "back to floor",
            trigger: ".floor-button",
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
export function selectedTableIs(name) {
    return [
        {
            content: `selected table is '${name}'`,
            trigger: `.floor-map .table.selected .label:contains("${name}")`,
            run: () => {},
        },
    ];
}
export function hasTable(name) {
    return [
        {
            content: `selected floor has '${name}' table`,
            trigger: `.floor-map .table .label:contains("${name}")`,
            run: () => {},
        },
    ];
}
export function tableSeatIs(table, val) {
    return [
        {
            content: `Unselect table`,
            trigger: `.floor-map`,
        },
        {
            content: `number of seats in table '${table}' is '${val}'`,
            trigger: `.floor-map .table .infos:has(.label:contains("${table}")) ~ .table-seats:contains("${val}")`,
            run: function () {},
        },
        {
            content: `click table '${table}'`,
            trigger: `.floor-map .table .label:contains("${table}")`,
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
export function tableIsNotSelected(name) {
    return [
        {
            content: `table '${name}' is not selected`,
            trigger: `.floor-map .table:not(.selected) .label:contains("${name}")`,
            run: function () {},
        },
    ];
}
