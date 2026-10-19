import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
import { click, queryOne } from "@odoo/hoot-dom";

setupInteractionWhiteList("website.a11y_checkbox_description");

describe.current.tags("interaction_dev");

function createTemplate({ labelClass, descriptionInnerHTML }) {
    return /* html */ `
        <div data-name="Field" class="s_website_form_field mb-3 col-12 s_website_form_custom s_website_form_required s_website_form_description_top" data-type="boolean">
            <label class="s_website_form_label ${labelClass}" for="odeosp06g4g4" style="width: 200px;">
                <span class="s_website_form_label_content">Custom Text</span>
                <span class="s_website_form_mark"> *</span>
            </label>
            <div class="form-check">
                <input type="checkbox" value="Yes" class="s_website_form_input form-check-input" name="Custom Text" required="" id="odeosp06g4g4" data-fill-with="undefined">
            </div>
            <span class="s_website_form_field_description small form-text text-muted" data-description-mark=" *">
                ${descriptionInnerHTML}
            </span>
        </div>
    `;
}

test("checkbox description serve as label when the label is hidden with class invisible", async () => {
    const template = createTemplate({
        labelClass: "invisible",
        descriptionInnerHTML: "<span>I agree to the Terms &amp; Conditions</span>",
    });
    const { core } = await startInteractions(template);

    expect(core.interactions).toHaveLength(1);
    expect("input").not.toBeChecked();
    await click(".s_website_form_field_description");
    expect("input").toBeChecked();
    const descriptionEl = queryOne(".s_website_form_field_description");
    expect("input").toHaveAttribute("aria-labelledby", descriptionEl.id);
});

test("checkbox description serve as label when the label is hidden with class d-none", async () => {
    const template = createTemplate({
        labelClass: "d-none",
        descriptionInnerHTML: "<span>Click me</span>",
    });
    const { core } = await startInteractions(template);

    expect(core.interactions).toHaveLength(1);
    expect("input").not.toBeChecked();
    await click(".s_website_form_field_description");
    expect("input").toBeChecked();
    const descriptionEl = queryOne(".s_website_form_field_description");
    expect("input").toHaveAttribute("aria-labelledby", descriptionEl.id);
});

test("checkbox description is not clickable when there is a label", async () => {
    const template = createTemplate({
        labelClass: "",
        descriptionInnerHTML: "<span>Description</span>",
    });
    const { core } = await startInteractions(template);

    expect(core.interactions).toHaveLength(0);
});

test("clicking on a checkbox description doesn't toggle the checkbox when the label is hidden but the target is a link", async () => {
    const template = createTemplate({
        labelClass: "invisible",
        descriptionInnerHTML:
            "<span>I agree to the <a href='/terms' id='link'> Terms &amp; <i>Conditions</i></a></span>",
    });
    const { core } = await startInteractions(template);

    expect(core.interactions).toHaveLength(1);
    expect("input").not.toBeChecked();
    await click("#link");
    expect("input").not.toBeChecked();
    await click("#link i");
    expect("input").not.toBeChecked();
});
