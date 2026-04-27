import { fields, models } from "@web/../tests/web_test_helpers";

export class ProductProduct extends models.Model {
    _name = "product.product";

    name = fields.Char({ string: "Product Name" });
    default_code = fields.Char({ string: "Default Code" });

    _records = [
        { id: 1, name: "name1", default_code: "AAAA" },
        { id: 2, name: "name2", default_code: "AAAB" },
        { id: 3, name: "name3", default_code: "AAAC" },
    ];

    _views = {
        kanban: `
            <kanban records_draggable="0" js_class="fsm_product_kanban">
                <templates>
                    <t t-name="card">
                        <field name="name"/>
                        <field name="default_code"/>
                        <div name="o_kanban_price"
                        t-attf-id="product-{{record.id.raw_value}}-price"
                        class="d-flex flex-column"/>
                    </t>
                </templates>
            </kanban>
        `,
    };
}
