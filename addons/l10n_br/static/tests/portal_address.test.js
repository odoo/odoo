import { expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import "@l10n_br/interactions/address";
import { CustomerAddress } from "@portal/interactions/address";
import { getInteraction, startInteraction } from "@web/../tests/public/helpers";
import { onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { Deferred } from "@web/core/utils/concurrency";

const address = `<div class="o_customer_address_fill"><div id="errors"></div>
    <form class="address_autoformat" data-company-country-code="BR">
        <input name="address_type" value="billing"/><input name="required_fields" value=""/>
        <select name="country_id"><option value="1" code="BR">Brazil</option><option value="2" code="US">USA</option></select>
        <div><select name="state_id"><option value="">Choose</option><option value="10" selected="selected">One</option><option value="20">Two</option></select></div>
        <div class="o_standard_address"><input name="street"/></div>
        <div class="o_extended_address"><input name="street_name"/></div>
        <input name="zip"/>
        <div class="o_select_city"><select name="city_id" class="form-select"><option value="">Choose</option><option value="100" state-id="10" zip-ranges="[01000-001 05999-999]" selected="selected">Old city</option><option value="200" state-id="20">New city</option></select></div>
        <button id="save_address" type="button">Save</button>
    </form></div>`;

const country = () => ({
    phone_code: 0,
    states: [
        [10, "One", "ONE"],
        [20, "Two", "TWO"],
    ],
    state_required: false,
    required_fields: [],
});

async function mountAddress() {
    const { core } = await startInteraction(CustomerAddress, address);
    const interaction = getInteraction(core, CustomerAddress);
    await interaction.countryChange;
    await animationFrame();
    return interaction;
}

test("initialization loads the country once and preserves the saved state", async () => {
    let calls = 0;
    onRpc("/my/address/country_info/1", () => {
        calls++;
        return country();
    });
    await mountAddress();
    expect(calls).toBe(1);
    expect('[name="state_id"]').toHaveValue("10");
    expect('[name="city_id"]').toHaveValue("100");
});

test("an obsolete country response cannot repeat ZIP selection over a newer city choice", async () => {
    const response = new Deferred();
    let delayNext = false;
    onRpc("/my/address/country_info/1", () => {
        if (delayNext) {
            delayNext = false;
            return response;
        }
        return country();
    });
    onRpc("/my/address/country_info/2", country);
    const interaction = await mountAddress();
    queryOne('[name="zip"]').value = "01000-001";
    delayNext = true;
    const pending = interaction.onChangeCountry();
    queryOne('[name="country_id"]').value = "2";
    await interaction.onChangeCountry();
    queryOne('[name="country_id"]').value = "1";
    await interaction.onChangeCountry();
    expect('[name="city_id"]').toHaveValue("100");
    const city = queryOne('[name="city_id"]');
    city.value = "200";
    city.dispatchEvent(new Event("change", { bubbles: true }));
    expect('[name="state_id"]').toHaveValue("20");
    response.resolve(country());
    await pending;
    expect('[name="city_id"]').toHaveValue("200");
    expect('[name="state_id"]').toHaveValue("20");
});

test("an initial country failure leaves the Brazilian address interaction retryable", async () => {
    expect.errors(1);
    let calls = 0;
    onRpc("/my/address/country_info/1", () => {
        if (++calls === 1) {
            throw new Error("initial Brazilian country lookup failed");
        }
        return country();
    });
    const { core } = await startInteraction(CustomerAddress, address);
    await animationFrame();
    expect.verifyErrors([/initial Brazilian country lookup failed/]);
    const interaction = getInteraction(core, CustomerAddress);
    patchWithCleanup(interaction.http, {
        post: async () => {
            expect.step("save");
            return { invalid_fields: [], messages: [] };
        },
    });
    queryOne("#save_address").click();
    await animationFrame();
    expect(calls).toBe(2);
    expect.verifySteps(["save"]);
});

test("country changes retain the active street fields in FormData", async () => {
    onRpc("/my/address/country_info/1", country);
    onRpc("/my/address/country_info/2", country);
    const interaction = await mountAddress();
    const form = queryOne("form");
    const brazilian = new FormData(form);
    expect(brazilian.has("street")).toBe(false);
    expect(brazilian.has("street_name")).toBe(true);
    queryOne('[name="country_id"]').value = "2";
    await interaction.onChangeCountry();
    const foreign = new FormData(form);
    expect(foreign.has("street")).toBe(true);
    expect(foreign.has("street_name")).toBe(false);
    expect('[name="city_id"]').toHaveClass("d-none");
});
