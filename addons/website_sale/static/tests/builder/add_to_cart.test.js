import { beforeEach, expect, test } from "@odoo/hoot";
import { contains, defineModels, models, fields } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";

class ProductProduct extends models.Model {
    _name = "product.product";
    name = fields.Char();
}
class ProductTemplate extends models.Model {
  _name = "product.template";
  name = fields.Char();
  is_published = fields.Boolean();
  sale_ok = fields.Boolean();
  product_variant_ids = fields.One2many({ relation: "product.product" });
  _records = [{ name: "Table", is_published: true, sale_ok: true, product_variant_ids: [] }];
}
defineWebsiteModels();
defineModels([ProductProduct, ProductTemplate]);

beforeEach(async () => {
    await setupWebsiteBuilderWithSnippet("s_add_to_cart");
});

test("disable add_to_cart button when there is no product", async () => {
    expect(":iframe .s_add_to_cart button").toHaveAttribute("disabled");

    await contains(":iframe .s_add_to_cart").click();
    await contains(".hb-row[data-label='Product'] button").click();
    await contains(".o_select_menu_item:contains(Table)").click();
    expect(":iframe .s_add_to_cart button").not.toHaveAttribute("disabled");
});
