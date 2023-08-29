/** @odoo-module */

import { createTourMethods } from "@point_of_sale/../tests/tours/helpers/utils";

class Do {
    clickTable(name) {
        return [
            {
                content: `click table '${name}'`,
                trigger: `.floor-map .table .label:contains("${name}")`,
            },
        ];
    }
    clickFloor(name) {
        return [
            {
                content: `click '${name}' floor`,
                trigger: `.floor-selector .button-floor:contains("${name}")`,
            },
        ];
    }
    clickEdit() {
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
    clickAddTable() {
        return [
            {
                content: "add table",
                trigger: `.edit-button i[aria-label=Add]`,
            },
        ];
    }
    clickDuplicate() {
        return [
            {
                content: "duplicate table",
                trigger: `.edit-button i[aria-label=Copy]`,
            },
        ];
    }
    clickRename() {
        return [
            {
                content: "rename table",
                trigger: `.edit-button i[aria-label=Rename]`,
            },
        ];
    }
    clickSeats() {
        return [
            {
                content: "change number of seats",
                trigger: `.edit-button i[aria-label=Seats]`,
            },
        ];
    }
    clickTrash() {
        return [
            {
                content: "trash table",
                trigger: `.edit-button.trash`,
            },
        ];
    }
    closeEdit() {
        return [
            {
                content: "Close edit mode",
                trigger: ".edit-button .close-edit-button",
            },
        ];
    }
    changeShapeTo(shape) {
        return [
            {
                content: `change shape to '${shape}'`,
                trigger: `.edit-button.button-option${shape === "round" ? ".round" : ".square"}`,
            },
        ];
    }
    ctrlClickTable(name) {
        return [
            {
                content: `ctrl click table '${name}'`,
                trigger: `.floor-map .table .label:contains("${name}")`,
                run() {
                    const el = this.$anchor[0];
                    el.dispatchEvent(new MouseEvent("click", { bubbles: true, ctrlKey: true }));
                },
            },
        ];
    }
}

class Check {
    selectedFloorIs(name) {
        return [
            {
                content: `selected floor is '${name}'`,
                trigger: `.floor-selector .button-floor.btn-primary:contains("${name}")`,
                run: () => {},
            },
        ];
    }
    selectedTableIs(name) {
        return [
            {
                content: `selected table is '${name}'`,
                trigger: `.floor-map .table.selected .label:contains("${name}")`,
                run: () => {},
            },
        ];
    }
    hasTable(name) {
        return [
            {
                content: `selected floor has '${name}' table`,
                trigger: `.floor-map .table .label:contains("${name}")`,
                run: () => {},
            },
        ];
    }
    tableSeatIs(table, val) {
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
    orderCountSyncedInTableIs(table, count) {
        return [
            {
                trigger: `.floor-map .table .label:contains("${table}") ~ .order-count:contains("${count}")`,
                run: function () {},
            },
        ];
    }
    isShown() {
        return [
            {
                trigger: ".floor-map",
                run: function () {},
            },
        ];
    }
    tableIsNotSelected(name) {
        return [
            {
                content: `table '${name}' is not selected`,
                trigger: `.floor-map .table:not(.selected) .label:contains("${name}")`,
                run: function () {},
            },
        ];
    }
}

class Execute {}

// FIXME: this is a horrible hack to export an object as named exports.
// eslint-disable-next-line no-undef
Object.assign(__exports, createTourMethods("FloorScreen", Do, Check, Execute));
