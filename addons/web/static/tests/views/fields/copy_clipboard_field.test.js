import { expect, test } from "@odoo/hoot";
import {
    contains,
    defineModels,
    fieldInput,
    fields,
    mockService,
    models,
    mountView,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    _name = "res.partner";

    char_field = fields.Char({
        string: "Char",
        default: "My little Char Value",
        trim: true,
    });

    _records = [
        {
            id: 1,
            char_field: "char value",
        },
    ];

    _views = {
        form: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="char_field" widget="CopyClipboardChar"/>
                    </group>
                </sheet>
            </form>`,
    };
}

defineModels([Partner]);

test("Char Field: Copy to clipboard button", async () => {
    await mountView({
        type: "form",
        resModel: "res.partner",
        resId: 1,
    });

    expect(".o_clipboard_button.o_btn_char_copy").toHaveCount(1);
});

test("Show copy button even on empty field", async () => {
    Partner._records.push({
        char_field: false,
    });

    await mountView({ type: "form", resModel: "res.partner", resId: 2 });

    expect(".o_field_CopyClipboardChar[name='char_field'] .o_clipboard_button").toHaveCount(1);
});

test("Show copy button even on readonly empty field", async () => {
    Partner._fields.char_field.readonly = true;
    await mountView({
        type: "form",
        resModel: "res.partner",
        arch: `
        <form>
            <sheet>
                <group>
                    <field name="char_field" widget="CopyClipboardChar" />
                </group>
            </sheet>
        </form>`,
    });

    expect(".o_field_CopyClipboardChar[name='char_field'] .o_clipboard_button").toHaveCount(1);
});

test("Display a tooltip on click", async () => {
    mockService("popover", {
        add(el, comp, params) {
            expect(params).toEqual({ tooltip: "Copied" });
            expect.step("copied tooltip");
            return () => {};
        },
    });

    patchWithCleanup(navigator.clipboard, {
        async writeText(text) {
            expect.step(text);
        },
    });

    await mountView({
        type: "form",
        resModel: "res.partner",
        resId: 1,
    });

    await expect(".o_clipboard_button.o_btn_char_copy").toHaveCount(1);
    await contains(".o_clipboard_button", { visible: false }).click();
    expect.verifySteps(["char value", "copied tooltip"]);
});

test("CopyClipboardButtonField in form view", async () => {
    patchWithCleanup(navigator.clipboard, {
        async writeText(text) {
            expect.step(text);
        },
    });

    await mountView({
        type: "form",
        resModel: "res.partner",
        resId: 1,
        arch: `
            <form>
                <group>
                    <field name="char_field" widget="CopyClipboardButton"/>
                </group>
            </form>`,
    });

    expect(".o_field_widget[name=char_field] input").toHaveCount(0);
    expect(".o_clipboard_button.o_btn_char_copy").toHaveCount(1);

    await contains(".o_clipboard_button.o_btn_char_copy").click();

    expect.verifySteps(["char value"]);
});

test("CopyClipboardButtonField can be disabled", async () => {
    patchWithCleanup(navigator.clipboard, {
        async writeText(text) {
            expect.step(text);
        },
    });

    await mountView({
        type: "form",
        resModel: "res.partner",
        resId: 1,
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="char_field" disabled="char_field == 'char value'" widget="CopyClipboardButton"/>
                        <field name="char_field" widget="char"/>
                    </group>
                </sheet>
            </form>`,
    });
    expect(".o_clipboard_button.o_btn_char_copy[disabled]").toHaveCount(1);
    await fieldInput("char_field").edit("another char value");
    expect(".o_clipboard_button.o_btn_char_copy[disabled]").toHaveCount(0);
});
