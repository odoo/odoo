/** @odoo-module */
/* global posmodel */

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import * as ProductScreen from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as Order from "@point_of_sale/../tests/tours/helpers/generic_components/OrderWidgetMethods";

class PosScaleDummy {
    action() {}
    removeListener() {}
    addListener(callback) {
        setTimeout(
            () =>
                callback({
                    status: "ok",
                    value: 2.35,
                }),
            1000
        );
        return Promise.resolve();
    }
}

registry.category("web_tour.tours").add("pos_iot_scale_tour", {
    url: "/web",
    test: true,
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            trigger: '.o_app[data-menu-xmlid="point_of_sale.menu_point_root"]',
        },
        {
            trigger: ".o_pos_kanban button.oe_kanban_action_button",
        },
        {
            trigger: ".pos .pos-content",
            run: function () {
                posmodel.hardwareProxy.deviceControllers.scale = new PosScaleDummy();
            },
        },
        ...ProductScreen.clickHomeCategory(),
        {
            trigger: '.opening-cash-control .button:contains("Open session")',
        },
        {
            trigger: '.product:contains("Whiteboard Pen")',
        },
        {
            trigger: '.js-weight:contains("2.35")',
        },
        {
            trigger: ".buy-product",
        },
        ...Order.hasLine({ quantity: "2.35" }),
        {
            trigger: ".menu-button",
        },
        {
            trigger: ".close-button",
        },
        {
            trigger: ".menu-button",
        },
        {
            trigger: ".close-button",
            run: function () {}, //it's a check,
        },
    ],
});
