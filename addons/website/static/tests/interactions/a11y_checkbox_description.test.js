import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
import { click, queryFirst } from "@odoo/hoot-dom";

setupInteractionWhiteList("website.a11y_checkbox_description");

describe.current.tags("interaction_dev");

test("checkbox description serve as label when the label is hidden with class invisible", async () => {
    const { core } = await startInteractions(`
     <div data-name="Field" class="s_website_form_field mb-3 col-12 s_website_form_custom s_website_form_required s_website_form_description_top" data-type="boolean" data-translated-name="Custom Text">
         <label class="s_website_form_label invisible" for="odeosp06g4g4" style="width: 200px;">
              <span class="s_website_form_label_content">Custom Text</span>
              <span class="s_website_form_mark"> *</span>
        </label>
        <div class="form-check">
            <input type="checkbox" value="Yes" class="s_website_form_input form-check-input" name="Custom Text" required="" id="odeosp06g4g4" data-fill-with="undefined">
        </div>
        <span class="s_website_form_field_description small form-text text-muted" data-description-mark=" *">
            <span>I agree to the Terms &amp; Conditions</span>
        </span>
      </div> `);

    expect(core.interactions).toHaveLength(1);

    const inputEl = queryFirst("input");
    const descriptionEl = queryFirst(".s_website_form_field_description");

    expect(inputEl.checked).toBe(false);
    await click(descriptionEl);
    expect(inputEl.checked).toBe(true);
});

test("checkbox description serve as label when the label is hidden with class d-none", async () => {
    const { core } = await startInteractions(`
      <div
          data-name="Field"
          class="s_website_form_field mb-3 col-12 s_website_form_custom s_website_form_required s_website_form_description_top"
          data-type="boolean"
          data-translated-name="Checkbox field"
      >
          <label
              class="s_website_form_label d-none"
              for="ohdq388h"
              style="width: 200px"
              ><span class="s_website_form_label_content">Checkbox field</span
              ><span class="s_website_form_mark"> *</span></label
          >
          <div class="form-check">
              <input
                  type="checkbox"
                  value="Yes"
                  class="s_website_form_input form-check-input"
                  name="Checkbox field"
                  required=""
                  id="ohdq388h"
                  data-fill-with="undefined"
              />
          </div>
          <span
              class="s_website_form_field_description small form-text text-muted"
              data-description-mark=" *"
              ><span>I agree to the Terms &amp; Conditions</span></span
          >
      </div>
      `);

    expect(core.interactions).toHaveLength(1);

    const inputEl = queryFirst("input");
    const descriptionEl = queryFirst(".s_website_form_field_description");

    expect(inputEl.checked).toBe(false);
    await click(descriptionEl);
    expect(inputEl.checked).toBe(true);
});

test("checkbox description is not clickable when there is a label", async () => {
    const { core } = await startInteractions(`
     <div data-name="Field" class="s_website_form_field mb-3 col-12 s_website_form_custom s_website_form_required s_website_form_description_top" data-type="boolean" data-translated-name="Custom Text">
         <label class="s_website_form_label" for="odeosp06g4g4" style="width: 200px;">
              <span class="s_website_form_label_content">Custom Text</span>
              <span class="s_website_form_mark"> *</span>
        </label>
        <div class="form-check">
            <input type="checkbox" value="Yes" class="s_website_form_input form-check-input" name="Custom Text" required="" id="odeosp06g4g4" data-fill-with="undefined">
        </div>
        <span class="s_website_form_field_description small form-text text-muted" data-description-mark=" *">
            <span>I agree to the Terms &amp; Conditions</span>
        </span>
      </div> `);

    expect(core.interactions).toHaveLength(0);

    const inputEl = queryFirst("input");
    const descriptionEl = queryFirst(".s_website_form_field_description");

    expect(inputEl.checked).toBe(false);
    await click(descriptionEl);
    expect(inputEl.checked).toBe(false);
});
