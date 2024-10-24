/** @odoo-module **/
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import * as Dialog from "@stock/../tests/tours/utils/dialog_util";

registry.category("web_tour.tours").add('test_enable_product_tracking', { test: true, steps: () => [
    {
        trigger: "div[name=is_storable] input",
        run: "click",
    },
    Dialog.is({ title: "Start Tracking" }),
    Dialog.bodyIs(
        "If you have this product in stock and your transfers require existing lot/serial number, you may run issues.\nAdjust your inventory to precise serials/lots in stock if necessary"
    ),
    Dialog.confirm("Track Product"),
    ...stepUtils.saveForm(),
]});

registry.category("web_tour.tours").add('test_disable_product_tracking', { test: true, steps: () => [
    {
        trigger: "div[name=is_storable] input",
        run: "click",
    },
    Dialog.is({ title: "Confirmation" }),
    Dialog.bodyIs(
        "Are you sure you want to stop tracking this product?\nAll existing tracability will be lost"
    ),
    Dialog.confirm("Yes"),
    ...stepUtils.saveForm(),
]});
