import { expect, test } from "@odoo/hoot";
import { animationFrame, press, waitFor } from "@odoo/hoot-dom";
import { MockServer, onRpc } from "@web/../tests/web_test_helpers";
import { setupAndMountPosApp } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import * as PosUiUtils from "@point_of_sale/../tests/unit/ui_utils";
import * as SaleUiUtils from "@pos_sale/../tests/unit/ui_utils";

const Utils = { ...PosUiUtils, ...SaleUiUtils };

definePosModels();

test("test_ecommerce_unpaid_order_is_shown_in_pos: orders that are not paid yet are listed", async () => {
    await setupAndMountPosApp();

    await Utils.openQuotationList();

    expect(Utils.isQuotationListed("S00001")).toBe(true);
});

test("PosOrderDoesNotRemainInList / test_ecommerce_paid_order_is_hidden_in_pos: a fully paid order is not listed", async () => {
    await setupAndMountPosApp();

    // Settling and paying the order in the PoS (or paying it through eCommerce)
    // leaves no unpaid amount on the sale order.
    MockServer.env["sale.order"].write([1], { amount_unpaid: 0 });

    await Utils.openQuotationList();

    expect(Utils.isQuotationListed("S00001")).toBe(false);
    expect(Utils.isQuotationListed("S00002")).toBe(true);

    await Utils.removeFilter("Not Paid");
    expect(Utils.isQuotationListed("S00001")).toBe(true);
    expect(Utils.isQuotationListed("S00002")).toBe(true);

    await Utils.selectFilter("Paid");
    expect(Utils.isQuotationListed("S00001")).toBe(true);
    expect(Utils.isQuotationListed("S00002")).toBe(false);
});

test("test_selected_partner_quotation_loading: the orders are restricted to the selected customer", async () => {
    const store = await setupAndMountPosApp();

    const domains = [];
    onRpc("sale.order", "web_search_read", ({ kwargs }) => void domains.push(kwargs.domain));

    await Utils.selectCustomer("Administrator");
    await Utils.openQuotationList();

    expect(domains.at(-1)).toInclude(["partner_id", "any", [["id", "child_of", [3]]]]);

    await press("escape");
    await animationFrame();
    store.addNewOrder();
    await animationFrame();

    await Utils.selectCustomer("User1");
    await Utils.openQuotationList();

    expect(domains.at(-1)).toInclude(["partner_id", "any", [["id", "child_of", [4]]]]);
});

test("PosOrdersListDifferentCurrency: orders of another currency are not listed", async () => {
    await setupAndMountPosApp();

    const saleOrderIds = MockServer.env["sale.order"].map((saleOrder) => saleOrder.id);
    MockServer.env["sale.order"].write(saleOrderIds, { currency_id: 125 });

    await Utils.openQuotationList();
    await waitFor(`.modal .o_nocontent_help:contains("No record found")`);

    expect(Utils.listedQuotationsCount()).toBe(0);
});
