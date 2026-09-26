import * as Portal from "@point_of_sale/../tests/pos/tours/utils/portal_util";
import { negateStep } from "@point_of_sale/../tests/generic_helpers/utils";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_portal_store_orders_list_tour", {
    steps: () =>
        [
            Portal.checkStoreOrdersShown(),
            Portal.openStoreOrders(),

            Portal.checkOrderShown("1000-002-00001"),
            Portal.checkOrderShown("1000-002-00002"),
            Portal.checkOrderShown("1000-002-00003"),
            Portal.checkReceiptLink("1000-002-00001"),
            Portal.checkInvoiceLink("1000-002-00001"),

            // Sorted on the date by default, so the most recent order comes first.
            Portal.checkFirstOrder("1000-002-00002"),
            Portal.sortBy("total_amount"),
            Portal.checkFirstOrder("1000-002-00001"),

            // Only the third order got a customer invoice of its own.
            Portal.filterBy("invoiced_order"),
            Portal.checkOrderShown("1000-002-00003"),
            negateStep(Portal.checkOrderShown("1000-002-00001")),
            negateStep(Portal.checkOrderShown("1000-002-00002")),

            Portal.filterBy("non_invoiced_order"),
            Portal.checkOrderShown("1000-002-00001"),
            Portal.checkOrderShown("1000-002-00002"),
            negateStep(Portal.checkOrderShown("1000-002-00003")),
        ].flat(),
});
