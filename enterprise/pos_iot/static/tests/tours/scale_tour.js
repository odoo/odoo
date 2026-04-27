/* global posmodel */

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import * as Order from "@point_of_sale/../tests/tours/utils/generic_components/order_widget_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";

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
    url: "/odoo",
    steps: () =>
        [
            stepUtils.showAppsMenuItem(),
            {
                trigger: '.o_app[data-menu-xmlid="point_of_sale.menu_point_root"]',
                run: "click",
            },
            {
                trigger: ".o_pos_kanban button.oe_kanban_action",
                run: "click",
            },
            Dialog.confirm("Open Register"),
            {
                trigger: ".pos .pos-content",
                run: function () {
                    posmodel.hardwareProxy.connectionInfo = {
                        status: "connected",
                        drivers: {
                            scale: {
                                status: "connected",
                            },
                        },
                    };
                    posmodel.hardwareProxy.deviceControllers.scale = new PosScaleDummy();
                },
            },
            {
                trigger: '.product:contains("Whiteboard Pen")',
                run: "click",
            },
            {
                trigger: '.gross-weight:contains("2.35")',
                run: "click",
            },
            {
                trigger: ".buy-product",
                run: "click",
            },
            ...Order.hasLine({ quantity: "2.35" }),
        ].flat(),
});
