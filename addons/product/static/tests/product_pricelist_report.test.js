import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import { contains, defineModels, fields, getService, models, mountWebClient, onRpc } from "@web/../tests/web_test_helpers";

class ProductProduct extends models.Model {
    _records = [{ id: 42, name: "Customizable Desk" }];

    name = fields.Char();
}

class ProductPricelist extends models.Model {
    _records = [
        { id: 1, name: "Public Pricelist" },
        { id: 2, name: "Test" },
    ];

    name = fields.Char();
}

defineModels([ProductProduct, ProductPricelist]);
defineMailModels();

test(`Pricelist Client Action`, async () => {
    onRpc("report.product.report_pricelist", "get_html", async () => "");

    await mountWebClient();
    await getService("action").doAction({
        id: 1,
        name: "Generate Pricelist Report",
        tag: "generate_pricelist_report",
        type: "ir.actions.client",
        context: {
            active_ids: [42],
            active_model: "product.product",
        },
    });

    // checking default pricelist
    expect(`select#pricelists > option:eq(0)`).toHaveText("Public Pricelist", {
        message: "should have default pricelist",
    });

    // changing pricelist
    await contains(`select#pricelists`).select("2");

    // check whether pricelist value has been updated or not
    expect(`select#pricelists > option:eq(0)`).toHaveText("Test", {
        message: "After pricelist change, the pricelist_id field should be updated",
    });

    // check default quantities should be there
    expect(queryAllTexts(`.o_badges_list .badge`)).toEqual(["1", "5", "10"]);

    // existing quantity can not be added.
    await contains(`.o_add_qty`).click();
    expect(queryAllTexts(`.o_badges_list .badge`)).toEqual(["1", "5", "10"]);
    expect(`.o_notification`).toHaveCount(1);
    expect(`.o_notification .o_notification_content`).toHaveText(
        "Quantity already present (1).",
        { message: "Existing Quantity can not be added" }
    );
    expect(`.o_notification .o_notification_bar`).toHaveClass("bg-info");
    await contains(`.o_notification_close`).click();
    expect(`.o_notification`).toHaveCount(0);

    // adding few more quantities to check.
    await contains(`.add-quantity-input`).edit("2", { confirm: false });
    await contains(`.o_add_qty`).click();
    expect(queryAllTexts(`.o_badges_list .badge`)).toEqual(["1", "2", "5", "10"]);
    expect(`.o_notification`).toHaveCount(0);

    await contains(`.add-quantity-input`).edit("3", { confirm: false });
    await contains(`.o_add_qty`).click();
    expect(queryAllTexts(`.o_badges_list .badge`)).toEqual(["1", "2", "3", "5", "10"]);
    expect(`.o_notification`).toHaveCount(0);

    // no more than 5 quantities can be used at a time
    await contains(`.add-quantity-input`).edit("4", { confirm: false });
    await contains(`.o_add_qty`).click();
    expect(queryAllTexts(`.o_badges_list .badge`)).toEqual(["1", "2", "3", "5", "10"]);
    expect(`.o_notification`).toHaveCount(1);
    expect(`.o_notification .o_notification_content`).toHaveText(
        "At most 5 quantities can be displayed simultaneously. Remove a selected quantity to add others.",
        { message: "Can not add more then 5 quantities" }
    );
    expect(`.o_notification .o_notification_bar`).toHaveClass("bg-warning");
});
