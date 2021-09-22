odoo.define('pos_restaurant.tour.FloorScreenTourMethods', function (require) {
    'use strict';

    const { createTourMethods } = require('point_of_sale.tour.utils');

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
                    content: `click edit button`,
                    trigger: `.floor-map .edit-button`,
                },
            ];
        }
        clickAddTable() {
            return [
                {
                    content: 'add table',
                    trigger: `.floor-map .edit-button i[aria-label=Add]`,
                },
            ];
        }
        clickDuplicate() {
            return [
                {
                    content: 'duplicate table',
                    trigger: `.floor-map .edit-button i[aria-label=Duplicate]`,
                },
            ];
        }
        clickRename() {
            return [
                {
                    content: 'rename table',
                    trigger: `.floor-map .edit-button i[aria-label=Rename]`,
                },
            ];
        }
        clickSeats() {
            return [
                {
                    content: 'change number of seats',
                    trigger: `.floor-map .edit-button i[aria-label=Seats]`,
                },
            ];
        }
        clickTrash() {
            return [
                {
                    content: 'trash table',
                    trigger: `.floor-map .edit-button.trash`,
                },
            ];
        }
        changeShapeTo(shape) {
            return [
                {
                    content: `change shape to '${shape}'`,
                    trigger: `.edit-button .button-option${shape === 'round' ? '.square' : '.round'}`,
                },
            ];
        }
    }

    class Check {
        selectedFloorIs(name) {
            return [
                {
                    content: `selected floor is '${name}'`,
                    trigger: `.floor-selector .button-floor.active:contains("${name}")`,
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
                    trigger: `.floor-map .tables .table .label:contains("${name}")`,
                    run: () => {},
                },
            ];
        }
        editModeIsActive(flag) {
            return [
                {
                    content: `check if edit mode is ${flag ? 'active' : 'inactive'}`,
                    trigger: `.floor-map .edit-button${flag ? '.active' : ':not(:has(.active))'}`,
                    run: () => {},
                },
            ];
        }
        tableSeatIs(table, val) {
            return [
                {
                    content: `number of seats in table '${table}' is '${val}'`,
                    trigger: `.floor-map .tables .table .label:contains("${table}") ~ .table-seats:contains("${val}")`,
                    run: function () {},
                },
            ];
        }
        orderCountSyncedInTableIs(table, count) {
            return [
                {
                    trigger: `.floor-map .table .order-count:contains("${count}") ~ .label:contains("${table}")`,
                    run: function () {},
                },
            ];
        }
        isShown() {
            return [
                {
                    trigger: '.floor-map',
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

    return createTourMethods('FloorScreen', Do, Check, Execute);
});
