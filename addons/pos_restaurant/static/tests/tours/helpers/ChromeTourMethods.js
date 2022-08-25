odoo.define('pos_restaurant.tour.ChromeTourMethods', function (require) {
    'use strict';

    const { createTourMethods } = require('point_of_sale.tour.utils');
    const { Do } = require('point_of_sale.tour.ChromeTourMethods');

    class DoExt extends Do {
        backToFloor() {
            return [
                {
                    content: 'back to floor',
                    trigger: '.floor-button',
                },
            ];
        }
    }

    class Check {
        backToFloorTextIs(floor, table) {
            return [
                {
                    content: `back to floor text is '${floor} ( ${table} )'`,
                    trigger: `.floor-button span:contains("${floor}") ~ .table-name:contains("(${table})")`,
                    run: () => {},
                },
            ];
        }
    }

    class Execute {}

    return createTourMethods('Chrome', DoExt, Check, Execute);
});
