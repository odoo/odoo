import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";

definePosModels();

test("test_refund_line_keep_attributes: refund line keeps variant attributes", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const attributeValue = store.models["product.template.attribute.value"].create({
        name: "Sugar",
        is_custom: false,
        price_extra: 0,
    });

    const line = await store.addLineToCurrentOrder({
        product_tmpl_id: store.models["product.template"].get(5),
        qty: 1,
    });
    line.attribute_value_ids = [attributeValue];
    order.state = "paid";

    const ticketScreen = await mountWithCleanup(TicketScreen);
    ticketScreen.onClickOrder(order);
    ticketScreen._onUpdateSelectedOrderline({ key: "Enter", buffer: "1" });
    await ticketScreen.onDoRefund();

    const refundOrder = store.getOrder();
    const refundLine = refundOrder.lines.find((l) => l.refunded_orderline_id?.id === line.id);
    expect(refundLine.attribute_value_ids).toHaveLength(1);
    expect(refundLine.attribute_value_ids[0].name).toBe("Sugar");
});
