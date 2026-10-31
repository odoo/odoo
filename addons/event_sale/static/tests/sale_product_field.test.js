import { expect, test } from "@odoo/hoot";
import { contains, defineModels, mockService, models, mountView } from "@web/../tests/web_test_helpers";
import { saleModels } from "@sale/../tests/sale_test_helpers";

class EventEvent extends models.ServerModel {
    _name = "event.event";

    _records = [{ id: 1, name: "Concert" }];
}

class EventSlot extends models.ServerModel {
    _name = "event.slot";

    _records = [{ id: 2, event_id: 1 }];
}

class EventEventTicket extends models.ServerModel {
    _name = "event.event.ticket";

    _records = [{ id: 3, name: "VIP", event_id: 1 }];
}

class ProductProduct extends saleModels.ProductProduct {
    _records = [{ id: 1, name: "Concert ticket", type: "service", service_tracking: "event" }];
}

class ProductTemplateAttributeValue extends models.ServerModel {
    _name = "product.template.attribute.value";
}

class SaleOrder extends saleModels.SaleOrder {
    _records = [{ id: 1, name: "S00001", order_line: [1] }];
}

class SaleOrderLine extends saleModels.SaleOrderLine {
    _records = [
        {
            id: 1,
            order_id: 1,
            name: "Concert",
            product_id: 1,
            event_id: 1,
            event_slot_id: 2,
            event_ticket_id: 3,
        },
    ];
}

defineModels({
    ...saleModels,
    ProductProduct,
    SaleOrder,
    SaleOrderLine,
    ProductTemplateAttributeValue,
    EventEvent,
    EventSlot,
    EventEventTicket,
});

test("event configurator is opened with the slot of the line", async () => {
    mockService("action", {
        doAction(action, { additionalContext }) {
            expect.step(additionalContext);
        },
    });
    await mountView({
        type: "form",
        resModel: "sale.order",
        resId: 1,
        arch: `
            <form>
                <field name="order_line">
                    <list editable="bottom">
                        <field name="product_id" widget="sol_product_many2one"/>
                        <field name="name"/>
                        <field name="event_id"/>
                        <field name="event_slot_id"/>
                        <field name="event_ticket_id"/>
                    </list>
                </field>
            </form>`,
    });
    await contains(".o_data_row .o_data_cell[name='product_id']").click();
    await contains(".o_data_row [name='product_id'] .fa-pencil").click();
    expect.verifySteps([
        {
            default_product_id: 1,
            default_event_id: 1,
            default_event_slot_id: 2,
            default_event_ticket_id: 3,
        },
    ]);
});
