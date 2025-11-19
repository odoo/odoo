import { setupHTMLBuilder } from "@html_builder/../tests/helpers";
import { expect, test, describe, animationFrame } from "@odoo/hoot";
import { click, manuallyDispatchProgrammaticEvent, queryOne } from "@odoo/hoot-dom";
import { pasteText } from "@html_editor/../tests/_helpers/user_actions";
import { nodeSize } from "@html_editor/utils/position";

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

test("should restrict the monetary field to digits, dot, and comma only", async () => {
    const { getEditor } = await setupHTMLBuilder(
        `<span data-oe-model="product.template" data-oe-id="9" data-oe-field="list_price" data-oe-type="monetary" data-oe-expression="product.list_price">
            $<span class="span-in-currency"/>&nbsp;<span class="oe_currency_value">5,000</span>
        </span>`
    );

    const editor = getEditor();
    const monetaryField = queryOne(":iframe span.span-in-currency span.oe_currency_value");

    // Cursor at end of monetary field.
    editor.shared.selection.focusEditable();
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
