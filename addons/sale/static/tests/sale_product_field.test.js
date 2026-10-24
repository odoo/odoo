import { startServer } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { advanceTime, animationFrame, Deferred } from "@odoo/hoot-mock";
import {
    clickSave,
    Command,
    contains,
    mountView,
    onRpc,
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

test("deleting sale order lines on a slow connection does not send a virtual delete", async () => {
    await startServer();
    let slowOnchange = null;
    onRpc("sale.order", "onchange", ({ args }) => {
        const commands = args[1].order_line || [];
        expect(commands.some(([cmd, id]) => cmd === 2 && typeof id === "string")).toBe(false, {
            message: "a virtual id must never be sent in a DELETE command",
        });
        return slowOnchange;
    });
    await mountView({
        type: "form",
        resModel: "sale.order",
        arch: `
            <form>
                <field name="order_line" widget="sol_o2m" on_change="1">
                    <list editable="bottom">
                        <field name="name" widget="sol_text"/>
                    </list>
                </field>
            </form>`,
    });

    await contains(".o_field_x2many_list_row_add a").click();
    await contains('div[name="name"] textarea').edit("First line", { confirm: "blur" });
    await contains(".o_field_x2many_list_row_add a").click();
    await contains('div[name="name"] textarea').edit("Second line", { confirm: "blur" });
    expect(".o_data_row").toHaveCount(2);

    // Throttle the connection: the onchange of the first deletion stays pending.
    slowOnchange = new Deferred();
    await contains(".o_data_row:eq(0) .o_list_record_remove").click();
    await animationFrame();
    // The first line is removed locally even though its onchange is still pending.
    expect(".o_data_row").toHaveCount(1);

    // Delete the second line twice, waiting out the remove button's 500ms debounce.
    await contains(".o_data_row:eq(0) .o_list_record_remove").click();
    await advanceTime(500);
    await contains(".o_data_row:eq(0) .o_list_record_remove").click();

    slowOnchange.resolve(); 
    await animationFrame();
    await animationFrame();
    expect(".o_data_row").toHaveCount(0);
});

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
