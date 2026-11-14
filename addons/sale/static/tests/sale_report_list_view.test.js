import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import { contains, defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";

class SaleReport extends models.Model {
    _name = "sale.report";

    name = fields.Char();
    product_uom_qty = fields.Float({ aggregator: "sum" });
    price_unit = fields.Float({ aggregator: "avg" });

    _records = [
        { id: 1, name: "S00001", product_uom_qty: 1, price_unit: 3 },
        { id: 2, name: "S00002", product_uom_qty: 5, price_unit: 12 },
    ];
}

defineModels([SaleReport]);
defineMailModels();

const arch = `
    <list js_class="sale_report_list">
        <field name="name"/>
        <field name="product_uom_qty" sum="Sum"/>
        <field name="price_unit" avg="Average"/>
    </list>
`;

test("unit price average is weighted by quantity", async () => {
    await mountView({ resModel: "sale.report", type: "list", arch });
    expect(queryAllTexts("tfoot td")).toEqual(["", "6.00", "10.50"]);

    await contains("tbody .o_list_record_selector input:eq(0)").click();
    expect(queryAllTexts("tfoot td")).toEqual(["", "1.00", "3.00"]);
});

test("unit price average is weighted by quantity across groups", async () => {
    await mountView({ resModel: "sale.report", type: "list", arch, groupBy: ["name"] });
    expect(queryAllTexts("tfoot td")).toEqual(["", "6.00", "10.50"]);
});
