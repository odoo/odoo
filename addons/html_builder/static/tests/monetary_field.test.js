import { setupHTMLBuilder } from "@html_builder/../tests/helpers";
import { expect, test, describe, animationFrame } from "@odoo/hoot";
import { click, manuallyDispatchProgrammaticEvent, queryOne } from "@odoo/hoot-dom";
import {
    pasteText,
    deleteBackward,
    deleteForward,
} from "@html_editor/../tests/_helpers/user_actions";
import { nodeSize } from "@html_editor/utils/position";
import { setSelection } from "@html_editor/../tests/_helpers/selection";
import { BuilderContentEditablePlugin } from "@html_builder/core/builder_content_editable_plugin";
import { MonetaryFieldPlugin } from "@html_builder/plugins/monetary_field_plugin";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { testEditor } from "@html_editor/../tests/_helpers/editor";
import { unformat } from "@html_editor/../tests/_helpers/format";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";

describe.current.tags("desktop");

test("should not allow edition of currency sign of monetary fields", async () => {
    await setupHTMLBuilder(
        `<span data-oe-model="product.template" data-oe-id="9" data-oe-field="list_price" data-oe-type="monetary" data-oe-expression="product.list_price">
            $&nbsp;<span class="oe_currency_value">750.00</span>
        </span>`
    );
    expect(":iframe span[data-oe-type]").toHaveProperty("isContentEditable", false);
    expect(":iframe span.oe_currency_value").toHaveProperty("isContentEditable", true);
});

test("clicking on the monetary field should select the amount", async () => {
    const { getEditor } = await setupHTMLBuilder(
        `<span data-oe-model="product.template" data-oe-id="9" data-oe-field="list_price" data-oe-type="monetary" data-oe-expression="product.list_price">
            $<span class="span-in-currency"/>&nbsp;<span class="oe_currency_value">750.00</span>
        </span>`
    );
    const editor = getEditor();
    await click(":iframe span.span-in-currency");
    expect(
        editor.shared.selection.areNodeContentsFullySelected(
            queryOne(":iframe span.oe_currency_value")
        )
    ).toBe(true, { message: "value of monetary field is selected" });
});

test("should make a span inside a monetary field be unremovable", async () => {
    const { getEditor } = await setupHTMLBuilder("", {
        headerContent: `
            <p>
                <span data-oe-model="product.template" data-oe-id="27" data-oe-field="list_price" data-oe-type="monetary" data-oe-expression="product.list_price" data-oe-xpath="/t[1]/div[1]/h3[2]/span[1]">
                    $&nbsp;
                    <span class="oe_currency_value"></span>
                </span>
            </p>
        `,
    });
    const currencyNode = queryOne(":iframe span.oe_currency_value");
    setSelection({ anchorNode: currencyNode, anchorOffset: 0 });
    deleteBackward(getEditor());
    expect(":iframe span.oe_currency_value").toHaveCount(1);
});

test("should restrict the monetary field to digits, dot, and comma only", async () => {
    const { getEditor } = await setupHTMLBuilder(
        `<span data-oe-model="product.template" data-oe-id="9" data-oe-field="list_price" data-oe-type="monetary" data-oe-expression="product.list_price">
            $<span class="span-in-currency"/>&nbsp;<span class="oe_currency_value">5,000</span>
        </span>`
    );

    const editor = getEditor();
    const monetaryField = queryOne(":iframe span.span-in-currency span.oe_currency_value");

    // Cursor at end of monetary field.
    editor.shared.selection.setSelection({
        anchorNode: monetaryField,
        anchorOffset: nodeSize(monetaryField),
    });
    await animationFrame();

    const testCharacters = [",", "1", "2", "3", ",", "4", "5", "6", ".", "7", "a", "$"];

    for (const char of testCharacters) {
        // Dispatch a beforeinput event to validate the character.
        const [beforeinputEvent] = await manuallyDispatchProgrammaticEvent.silent(
            monetaryField,
            "beforeinput",
            {
                inputType: "insertText",
                data: char,
            }
        );

        // If the character is blocked, skip insertion.
        if (!beforeinputEvent.defaultPrevented) {
            editor.document.execCommand("insertText", false, char);
        }
    }

    expect(monetaryField.textContent).toBe("5,000,123,456.7");
});

test("should keep only digits, dot, and comma when pasting into a monetary field", async () => {
    const { getEditor } = await setupHTMLBuilder(
        `<span data-oe-model="product.template" data-oe-id="9" data-oe-field="list_price" data-oe-type="monetary" data-oe-expression="product.list_price">
            $<span class="span-in-currency"/>&nbsp;<span class="oe_currency_value">750.00</span>
        </span>`
    );

    const editor = getEditor();
    const monetaryField = queryOne(":iframe span.span-in-currency span.oe_currency_value");

    // Select the entire monetary field.
    await click(monetaryField);
    await animationFrame();
    expect(editor.shared.selection.areNodeContentsFullySelected(monetaryField)).toBe(true);

    pasteText(editor, "1.234.56 extra text 7.891");
    expect(monetaryField).toHaveText("1.234.567.891");

    editor.shared.selection.setCursorEnd(monetaryField);
    await animationFrame();

    pasteText(editor, "Text: ,25");
    expect(monetaryField).toHaveText("1.234.567.891,25");
});

test("should make a span inside a monetary field be unremovable (1)", async () => {
    defineMailModels();
    await testEditor({
        contentBefore: unformat(`
            <p>
                <span data-oe-type="monetary" data-oe-field="list_price" class="o_savable">
                    $&nbsp;
                    <span class="oe_currency_value" data-oe-zws-empty-inline="">[]\u200b</span>
                </span>
            </p>
        `),
        contentBeforeEdit: unformat(`
                <p>
                    <span data-oe-type="monetary" data-oe-field="list_price" class="o_savable" contenteditable="false">
                        $&nbsp;
                        <span class="oe_currency_value" data-oe-zws-empty-inline="" contenteditable="true">[]\u200b</span>
                    </span>
                </p>
            `),
        stepFunction: deleteBackward,
        contentAfterEdit: unformat(`
            <p>
                <span data-oe-type="monetary" data-oe-field="list_price" class="o_savable" contenteditable="false">
                    $&nbsp;
                    <span class="oe_currency_value" data-oe-zws-empty-inline="" contenteditable="true">[\u200b]</span>
                </span>
            </p>
        `),
        contentAfter: unformat(`
                <p>
                    <span data-oe-type="monetary" data-oe-field="list_price" class="o_savable">
                        $&nbsp;
                        <span class="oe_currency_value" data-oe-zws-empty-inline="">[\u200b]</span>
                    </span>
                </p>
            `),
        config: {
            Plugins: [...MAIN_PLUGINS, MonetaryFieldPlugin, BuilderContentEditablePlugin],
            cleanEmptyStructuralContainers: false,
        },
    });
});

test("should make a span inside a monetary field be unremovable (2)", async () => {
    defineMailModels();
    await testEditor({
        contentBefore: unformat(`
            <p>
                <span data-oe-type="monetary" data-oe-field="list_price" class="o_savable">
                    <span class="oe_currency_value" data-oe-zws-empty-inline="">\u200b[]</span>$&nbsp;
                </span>
            </p>
        `),
        contentBeforeEdit: unformat(`
                <p>
                    <span data-oe-type="monetary" data-oe-field="list_price" class="o_savable" contenteditable="false">
                        <span class="oe_currency_value" data-oe-zws-empty-inline="" contenteditable="true">\u200b[]</span>$&nbsp;
                    </span>
                </p>
            `),
        stepFunction: deleteForward,
        contentAfterEdit: unformat(`
            <p>
                <span data-oe-type="monetary" data-oe-field="list_price" class="o_savable" contenteditable="false">
                    <span class="oe_currency_value" data-oe-zws-empty-inline="" contenteditable="true">[\u200b]</span>$&nbsp;
                </span>
            </p>
        `),
        contentAfter: unformat(`
                <p>
                    <span data-oe-type="monetary" data-oe-field="list_price" class="o_savable">
                        <span class="oe_currency_value" data-oe-zws-empty-inline="">[\u200b]</span>$&nbsp;
                    </span>
                </p>
            `),
        config: {
            Plugins: [...MAIN_PLUGINS, MonetaryFieldPlugin, BuilderContentEditablePlugin],
            cleanEmptyStructuralContainers: false,
        },
    });
});
