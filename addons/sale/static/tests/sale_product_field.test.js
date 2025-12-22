import { startServer } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import {
    clickSave,
    Command,
    contains,
    mountView,
    serverState,
} from "@web/../tests/web_test_helpers";
import { ProductProduct } from "./mock_server/mock_models/product_product";
import { defineSaleModels } from "./sale_test_helpers";

const WithTranslatedNameForm = `
    <form>
        <field name="order_line" widget="sol_o2m" mode="list">
            <list editable="bottom">
                <field name="product_id" widget="sol_product_many2one"/>
                <field name="product_template_id" widget="sol_product_many2one"/>
                <field name="name" widget="sol_text"/>
                <field name="translated_product_name" column_invisible="1"/>
            </list>
        </field>
    </form>
`;
const WithoutTranslatedNameForm = `
    <form>
        <field name="order_line" widget="sol_o2m" mode="list">
            <list editable="bottom">
                <field name="product_id" widget="sol_product_many2one"/>
                <field name="product_template_id" widget="sol_product_many2one"/>
                <field name="name" widget="sol_text"/>
            </list>
        </field>
    </form>
`;

defineSaleModels();

test("On updated form, product name should stay hidden", async () => {
    const product = ProductProduct._records[0];
    const pyEnv = await startServer();
    const soId = pyEnv["sale.order"].create({
        partner_id: serverState.partnerId,
        order_line: [
            Command.create({
                product_id: product.id,
                name: product.name.concat("\nA description"),
                translated_product_name: "Produit de test",
            }),
        ],
    });
    await mountView({
        type: "form",
        resModel: "sale.order",
        resId: soId,
        arch: WithTranslatedNameForm,
    });

    expect(".o_field_product_label_section_and_note_cell textarea").toHaveValue("A description");
});

test("On updated form, translated product name should be hidden if present", async () => {
    const product = ProductProduct._records[0];
    const pyEnv = await startServer();
    const translatedProductName = "Produit de test";
    const soId = pyEnv["sale.order"].create({
        partner_id: serverState.partnerId,
        order_line: [
            Command.create({
                product_id: product.id,
                name: translatedProductName.concat("\nA description"),
                translated_product_name: translatedProductName,
            }),
        ],
    });
    await mountView({
        type: "form",
        resModel: "sale.order",
        resId: soId,
        arch: WithTranslatedNameForm,
    });

    expect(".o_field_product_label_section_and_note_cell textarea").toHaveValue("A description");
});

test("On outdated form, should continue to hide product name", async () => {
    const product = ProductProduct._records[0];
    const pyEnv = await startServer();
    const soId = pyEnv["sale.order"].create({
        partner_id: serverState.partnerId,
        order_line: [
            Command.create({
                product_id: product.id,
                name: product.name.concat("\nA description"),
                translated_product_name: "Produit de test",
            }),
        ],
    });
    await mountView({
        type: "form",
        resModel: "sale.order",
        resId: soId,
        arch: WithoutTranslatedNameForm,
    });

    expect(".o_field_product_label_section_and_note_cell textarea").toHaveValue("A description");
});

test("On outdated form and translated product name already in the SOL name, should not hide the translated product name", async () => {
    const product = ProductProduct._records[0];
    const pyEnv = await startServer();
    const translatedProductName = "Produit de test";
    const soId = pyEnv["sale.order"].create({
        partner_id: serverState.partnerId,
        order_line: [
            Command.create({
                product_id: product.id,
                name: product.name.concat("\n", translatedProductName, "\nA description"),
                translated_product_name: translatedProductName,
            }),
        ],
    });
    await mountView({
        type: "form",
        resModel: "sale.order",
        resId: soId,
        arch: WithoutTranslatedNameForm,
    });

    expect(".o_field_product_label_section_and_note_cell textarea").toHaveValue(
        translatedProductName.concat("\nA description")
    );
});

test("On outdated form, editing the description should work as before", async () => {
    const product = ProductProduct._records[0];
    const pyEnv = await startServer();
    const translatedProductName = "Produit de test";
    const soId = pyEnv["sale.order"].create({
        partner_id: serverState.partnerId,
        order_line: [
            Command.create({
                product_id: product.id,
                name: product.name.concat("\nsomething wrong"),
                translated_product_name: translatedProductName,
            }),
        ],
    });
    const [so] = pyEnv["sale.order"].browse(soId);
    const [sol] = pyEnv["sale.order.line"].browse(so.order_line);
    await mountView({
        type: "form",
        resModel: "sale.order",
        resId: soId,
        arch: WithoutTranslatedNameForm,
    });

    await contains(".o_field_product_label_section_and_note_cell textarea").edit("A description");
    await clickSave();

    expect(".o_field_product_label_section_and_note_cell textarea").toHaveValue("A description");
    expect(sol.name).toBe(product.name.concat("\nA description"));
});

test("On updated form, editing the description shouldn't show the translated product name", async () => {
    const product = ProductProduct._records[0];
    const pyEnv = await startServer();
    const translatedProductName = "Produit de test";
    const soId = pyEnv["sale.order"].create({
        partner_id: serverState.partnerId,
        order_line: [
            Command.create({
                product_id: product.id,
                name: product.name.concat("\nsomething wrong"),
                translated_product_name: translatedProductName,
            }),
        ],
    });
    const [so] = pyEnv["sale.order"].browse(soId);
    const [sol] = pyEnv["sale.order.line"].browse(so.order_line);
    await mountView({
        type: "form",
        resModel: "sale.order",
        resId: soId,
        arch: WithTranslatedNameForm,
    });

    await contains(".o_field_product_label_section_and_note_cell textarea").edit("A description");
    await clickSave();

    expect(".o_field_product_label_section_and_note_cell textarea").toHaveValue("A description");
    expect(sol.name).toBe(translatedProductName.concat("\nA description"));
});

test("No description should be shown if there does not exist one apart from the product name", async () => {
    const product = ProductProduct._records[0];
    const pyEnv = await startServer();
    const translatedProductName = "Produit de test";
    const soId = pyEnv["sale.order"].create({
        partner_id: serverState.partnerId,
        order_line: [
            Command.create({
                product_id: product.id,
                name: product.name,
                translated_product_name: translatedProductName,
            }),
        ],
    });
    await mountView({
        type: "form",
        resModel: "sale.order",
        resId: soId,
        arch: WithTranslatedNameForm,
    });

    expect(".o_field_product_label_section_and_note_cell textarea").not.toHaveCount();
});

test("No description should be shown if there does not exist one apart from the translated product name", async () => {
    const product = ProductProduct._records[0];
    const pyEnv = await startServer();
    const translatedProductName = "Produit de test";
    const soId = pyEnv["sale.order"].create({
        partner_id: serverState.partnerId,
        order_line: [
            Command.create({
                product_id: product.id,
                name: translatedProductName,
                translated_product_name: translatedProductName,
            }),
        ],
    });
    await mountView({
        type: "form",
        resModel: "sale.order",
        resId: soId,
        arch: WithTranslatedNameForm,
    });

    expect(".o_field_product_label_section_and_note_cell textarea").not.toHaveCount();
});
