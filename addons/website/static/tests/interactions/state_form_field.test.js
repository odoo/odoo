import { animationFrame, describe, expect, queryAll, queryOne, test } from "@odoo/hoot";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";

setupInteractionWhiteList("website.state_form_field");

describe.current.tags("interaction_dev");

const formEl = `<section class="s_website_form"><form data-model_name="mail.mail">
        <div data-name="Country" class="s_website_form_field s_website_form_custom" data-type="many2one">
            <div>
                <label class="s_website_form_label" for="country">
                    <span class="s_website_form_label_content">Country</span>
                </label>
                <div>
                    <select class="form-select s_website_form_input" name="country_id" id="country">
                        <option value=""></option>
                        <option value="1" selected="selected">Country 1 (A)</option>
                        <option value="2">Country 2 (B)</option>
                        <option value="3">Country 3 (C)</option>
                    </select>
                </div>
            </div>
        </div>
        <div data-name="State" class="s_website_form_field s_website_form_custom" data-type="many2one">
            <div>
                <label class="s_website_form_label" for="state">
                    <span class="s_website_form_label_content">State</span>
                </label>
                <div>
                    <select class="form-select s_website_form_input" data-link-state-to-country="true" name="state_id" id="state">
                        <option value=""></option>
                        <option data-country-id="1" value="s1">State 1 (A)</option>
                        <option data-country-id="2" value="s2">State 2 (B)</option>
                        <option data-country-id="2" value="s3">State 3 (B)</option>
                        <option data-country-id="1" value="s4">State 4 (A)</option>
                        <option data-country-id="2" value="s5">State 5 (B)</option>
                    </select>
                </div>
            </div>
        </div>
    </form></section>`;

test("States are linked to the selected country", async () => {
    const { core } = await startInteractions(formEl);

    expect(core.interactions).toHaveLength(1);

    expect(".s_website_form_input[name='country_id']").toHaveValue("1");
    expect(".s_website_form_input[name='state_id'] > option").toHaveCount(3);
    expect(
        queryAll(".s_website_form_input[name='state_id'] > option").every(
            (option) => !option.value || option.dataset.countryId === "1"
        )
    ).toBe(true);

    const countryField = queryOne(".s_website_form_input[name='country_id']");
    countryField.value = "2";
    countryField.dispatchEvent(new Event("change"));
    await animationFrame();

    expect(".s_website_form_input[name='state_id'] > option").toHaveCount(4);
    expect(
        queryAll(".s_website_form_input[name='state_id'] > option").every(
            (option) => !option.value || option.dataset.countryId === "2"
        )
    ).toBe(true);
});

test("Country selected should be updated when changing state", async () => {
    const { core } = await startInteractions(formEl);

    expect(core.interactions).toHaveLength(1);
    const countryField = queryOne(".s_website_form_input[name='country_id']");
    const stateField = queryOne(".s_website_form_input[name='state_id']");

    countryField.value = "";
    countryField.dispatchEvent(new Event("change"));
    await animationFrame();

    expect(".s_website_form_input[name='country_id']").toHaveValue("");
    expect(".s_website_form_input[name='state_id'] > option").toHaveCount(6);
    stateField.value = "s5";
    stateField.dispatchEvent(new Event("change"));
    await animationFrame();
    expect(".s_website_form_input[name='country_id']").toHaveValue("2");
});

test("When the selected country has no states, the state field should be disabled", async () => {
    const { core } = await startInteractions(formEl);

    expect(core.interactions).toHaveLength(1);
    const countryField = queryOne(".s_website_form_input[name='country_id']");

    expect(".s_website_form_input[name='state_id']").not.toHaveAttribute("disabled", "disabled");

    countryField.value = "3";
    countryField.dispatchEvent(new Event("change"));
    await animationFrame();

    expect(".s_website_form_input[name='state_id']").toHaveAttribute("disabled");
});
