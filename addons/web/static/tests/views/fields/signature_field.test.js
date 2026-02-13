import { NameAndSignature } from "@web/core/signature/name_and_signature";

import { expect, queryOne, test } from "@odoo/hoot";
import { animationFrame, runAllTimers } from "@odoo/hoot-mock";
import { click, drag, edit, queryFirst, waitFor } from "@odoo/hoot-dom";
import {
    clickSave,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

function getUnique(target) {
    const src = target.dataset.src;
    return new URL(src).searchParams.get("unique");
}

class Partner extends models.Model {
    name = fields.Char();
    product_id = fields.Many2one({
        string: "Product Name",
        relation: "product",
    });
    sign = fields.Binary({ string: "Signature" });
    _records = [
        {
            id: 1,
            name: "Pop's Chock'lit",
            product_id: 7,
        },
    ];
}
class Product extends models.Model {
    name = fields.Char({ string: "Product Name" });
    _records = [
        {
            id: 7,
            name: "Veggie Burger",
        },
    ];
}
defineModels([Partner, Product]);

test("signature can be drawn", async () => {
    onRpc("/web/sign/get_fonts/", () => ({}));
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `<form><field name="sign" widget="signature" /></form>`,
    });

    expect("div[name=sign] img.o_signature").toHaveCount(0);
    expect("div[name=sign] div.o_signature svg").toHaveCount(1, {
        message: "should have a valid signature widget",
    });

    // Click on the widget to open signature modal
    await click("div[name=sign] div.o_signature");
    await waitFor(".modal .modal-body");
    expect(".modal .modal-body .o_web_sign_name_and_signature").toHaveCount(1);
    expect(".modal .btn.btn-primary:not([disabled])").toHaveCount(0);

    // Use a drag&drop simulation to draw a signature
    const { drop } = await drag(".modal .o_web_sign_signature", {
        position: {
            x: 1,
            y: 1,
        },
        relative: true,
    });
    await drop(".modal .o_web_sign_signature", {
        position: {
            x: 10, // Arbitrary value
            y: 10, // Arbitrary value
        },
        relative: true,
    });
    await animationFrame(); // await owl rendering
    expect(".modal .btn.btn-primary:not([disabled])").toHaveCount(1);

    // Click on "Adopt and Sign" button
    await click(".modal .btn.btn-primary:not([disabled])");
    await animationFrame();
    expect(".modal").toHaveCount(0);

    // The signature widget should now display the signature img
    expect("div[name=sign] div.o_signature svg").toHaveCount(0);
    expect("div[name=sign] img.o_signature").toHaveCount(1);

    const signImgSrc = queryFirst("div[name=sign] img.o_signature").dataset.src;
    expect(signImgSrc).not.toMatch("placeholder");
    expect(signImgSrc).toMatch(/^data:image\/png;base64,/);
});

test("Set simple field in 'full_name' node option", async () => {
    patchWithCleanup(NameAndSignature.prototype, {
        setup() {
            super.setup(...arguments);
            expect.step(this.props.signature.name);
        },
    });
    onRpc("/web/sign/get_fonts/", () => ({}));
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <field name="name"/>
                <field name="sign" widget="signature" options="{'full_name': 'name'}" />
            </form>`,
    });

    expect("div[name=sign] div.o_signature svg").toHaveCount(1, {
        message: "should have a valid signature widget",
    });
    // Click on the widget to open signature modal
    await click("div[name=sign] div.o_signature");
    await animationFrame();
    expect(".modal .modal-body a.o_web_sign_auto_button").toHaveCount(1, {
        message: 'should open a modal with "Auto" button',
    });
    expect(".o_web_sign_auto_button").toHaveClass("active", {
        message: "'Auto' panel is visible by default",
    });
    expect.verifySteps(["Pop's Chock'lit"]);
});

test("Set m2o field in 'full_name' node option", async () => {
    patchWithCleanup(NameAndSignature.prototype, {
        setup() {
            super.setup(...arguments);
            expect.step(this.props.signature.name);
        },
    });
    onRpc("/web/sign/get_fonts/", () => ({}));

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <field name="product_id"/>
                <field name="sign" widget="signature" options="{'full_name': 'product_id'}" />
            </form>`,
    });

    expect("div[name=sign] div.o_signature svg").toHaveCount(1, {
        message: "should have a valid signature widget",
    });

    // Click on the widget to open signature modal
    await click("div[name=sign] div.o_signature");
    await waitFor(".modal .modal-body");

    expect(".modal .modal-body a.o_web_sign_auto_button").toHaveCount(1, {
        message: 'should open a modal with "Auto" button',
    });
    expect.verifySteps(["Veggie Burger"]);
});

test("Set size (width and height) in node option", async () => {
    Partner._fields.sign2 = fields.Binary({ string: "Signature" });
    Partner._fields.sign3 = fields.Binary({ string: "Signature" });
    onRpc("/web/sign/get_fonts/", () => ({}));

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <field name="sign" widget="signature" options="{'size': [150,'']}" />
                <field name="sign2" widget="signature" options="{'size': ['',100]}" />
                <field name="sign3" widget="signature" options="{'size': [120,130]}" />
            </form>`,
    });

    expect(".o_signature").toHaveCount(3);

    expect("[name='sign'] .o_signature").toHaveStyle({
        width: "150px",
        height: "50px",
    });
    expect("[name='sign2'] .o_signature").toHaveStyle({
        width: "300px",
        height: "100px",
    });
    expect("[name='sign3'] .o_signature").toHaveStyle({
        width: "120px",
        height: "40px",
    });
});

test("clicking save manually after changing signature should change the unique of the image src", async () => {
    Partner._fields.foo = fields.Char({
        onChange() {},
    });

    const rec = Partner._records.find((rec) => rec.id === 1);
    rec.sign = "3 kb";
    rec.write_date = "2022-08-05 08:37:00"; // 1659688620000
    const fillSignatureField = async (lineToX, lineToY) => {
        await click(".o_field_signature img", { visible: false });
        await waitFor(".modal .modal-body");
        expect(".modal canvas").toHaveCount(1);
        const { drop } = await drag(".modal .o_web_sign_signature", {
            position: {
                x: 1,
                y: 1,
            },
            relative: true,
        });
        await drop(".modal .o_web_sign_signature", {
            position: {
                x: lineToX,
                y: lineToY,
            },
            relative: true,
        });
        await animationFrame();
        await click(".modal-footer .btn-primary");
        await animationFrame();
    };
    // 1659692220000, 1659695820000
    const lastUpdates = ["2022-08-05 09:37:00", "2022-08-05 10:37:00"];
    let index = 0;

    onRpc("/web/sign/get_fonts/", () => ({}));
    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        args[1].write_date = lastUpdates[index];
        args[1].sign = "4 kb";
        index++;
    });

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <field name="foo" />
                <field name="sign" widget="signature" />
            </form>`,
    });
    expect(getUnique(queryFirst(".o_field_signature img"))).toBe("1659688620000");

    await fillSignatureField(0, 2);
    await click(".o_field_widget[name='foo'] input");
    await edit("grrr", { confirm: "Enter" });
    await runAllTimers();
    await animationFrame();
    await clickSave();
    expect.verifySteps(["web_save"]);
    expect(getUnique(queryFirst(".o_field_signature img"))).toBe("1659692220000");

    await fillSignatureField(2, 0);
    await clickSave();
    expect.verifySteps(["web_save"]);
    expect(getUnique(queryFirst(".o_field_signature img"))).toBe("1659695820000");
});

test("save record with signature field modified by onchange", async () => {
    const MYB64 = `iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAYAAABytg0kAAAAAXNSR0IArs4c6QAAABRJREFUGFdjZGD438DAwNjACGMAACQlBAMW7JulAAAAAElFTkSuQmCC`;

    Partner._fields.foo = fields.Char({
        onChange(data) {
            data.sign = MYB64;
        },
    });

    const rec = Partner._records.find((rec) => rec.id === 1);
    rec.sign = "3 kb";
    rec.write_date = "2022-08-05 08:37:00"; // 1659688620000

    // 1659692220000, 1659695820000
    const lastUpdates = ["2022-08-05 09:37:00", "2022-08-05 10:37:00"];
    let index = 0;
    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        args[1].write_date = lastUpdates[index];
        args[1].sign = "4 kb";
        index++;
    });
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <field name="foo" />
                <field name="sign" widget="signature" />
            </form>`,
    });
    expect(getUnique(queryFirst(".o_field_signature img"))).toBe("1659688620000");
    await click("[name='foo'] input");
    await edit("grrr", { confirm: "Enter" });
    await runAllTimers();
    await animationFrame();
    expect(queryFirst("div[name=sign] img").dataset.src).toBe(`data:image/png;base64,${MYB64}`);

    await clickSave();
    expect(getUnique(queryFirst(".o_field_signature img"))).toBe("1659692220000");
    expect.verifySteps(["web_save"]);
});

test("signature field should render initials", async () => {
    patchWithCleanup(NameAndSignature.prototype, {
        setup() {
            super.setup(...arguments);
            expect.step(this.getCleanedName());
        },
    });
    onRpc("/web/sign/get_fonts/", () => ({}));

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <field name="product_id"/>
                <field name="sign" widget="signature" options="{'full_name': 'product_id', 'type': 'initial'}" />
            </form>`,
    });

    expect("div[name=sign] div.o_signature svg").toHaveCount(1, {
        message: "should have a valid signature widget",
    });

    // Click on the widget to open signature modal
    await click("div[name=sign] div.o_signature");
    await animationFrame();
    expect(".modal .modal-body a.o_web_sign_auto_button").toHaveCount(1, {
        message: 'should open a modal with "Auto" button',
    });
    expect.verifySteps(["V.B."]);
});

test("error loading url", async () => {
    Partner._records = [{
        id: 1,
        sign: "1 kb",
    }]
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <field name="sign" widget="signature" />
            </form>`,
    });
    const img = queryOne(".o_field_widget img");
    img.dispatchEvent(new Event("error"));
    await waitFor(".o_notification:has(.bg-danger):contains(Could not display the selected image)");
});
