import { expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import "@l10n_pe/interactions/address";
import { CustomerAddress } from "@portal/interactions/address";
import { getInteraction, startInteraction } from "@web/../tests/public/helpers";
import { onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { Deferred } from "@web/core/utils/concurrency";

const address = `<div class="o_customer_address_fill"><div id="errors"></div>
    <form class="address_autoformat" data-company-country-code="PE">
        <input name="address_type" value="billing"/><input name="required_fields" value=""/>
        <select name="country_id"><option value="1" code="PE">Peru</option><option value="2" code="US">USA</option></select>
        <div><select name="state_id"><option value="">Choose</option><option value="10" selected="selected">One</option><option value="20">Two</option></select></div>
        <div><input name="city"/></div>
        <div><select name="city_id"><option value="">Choose</option><option value="100" selected="selected">Old city</option><option value="200">New city</option></select></div>
        <div><select name="l10n_pe_district"><option value="">Choose</option><option value="1000" selected="selected">Old district</option></select></div>
        <button id="save_address" type="button">Save</button>
    </form></div>`;

async function mountAddress() {
    for (const id of [1, 2]) {
        onRpc(`/my/address/country_info/${id}`, () => ({
            phone_code: 0,
            states: [
                [10, "One", "ONE"],
                [20, "Two", "TWO"],
            ],
            state_required: false,
            required_fields:
                id === 1 ? ["state_id", "city_id", "l10n_pe_district"] : [],
        }));
    }
    const { core } = await startInteraction(CustomerAddress, address);
    const interaction = getInteraction(core, CustomerAddress);
    await interaction.countryChange;
    return interaction;
}

test("a late state response cannot replace the current state's cities", async () => {
    const first = new Deferred();
    onRpc("/portal/state_infos/10", () => first);
    onRpc("/portal/state_infos/20", () => ({ cities: [[200, "New city", "NEW"]] }));
    const interaction = await mountAddress();
    const pending = interaction.onChangeState();
    await animationFrame();
    queryOne('[name="state_id"]').value = "20";
    await interaction.onChangeState();
    first.resolve({ cities: [[100, "Old city", "OLD"]] });
    await pending;
    expect('[name="city_id"] option:last-child').toHaveValue("200");
    expect('[name="l10n_pe_district"] option').toHaveCount(1);
});

test("a late city response cannot replace the current city's districts", async () => {
    const first = new Deferred();
    onRpc("/portal/city_infos/100", () => first);
    onRpc("/portal/city_infos/200", () => ({
        districts: [[2000, "New district", "NEW"]],
    }));
    const interaction = await mountAddress();
    const pending = interaction.onChangeCity();
    await animationFrame();
    queryOne('[name="city_id"]').value = "200";
    await interaction.onChangeCity();
    first.resolve({ districts: [[1000, "Old district", "OLD"]] });
    await pending;
    expect('[name="l10n_pe_district"] option:last-child').toHaveValue("2000");
});

test("a state change immediately removes obsolete city and district selections", async () => {
    const response = new Deferred();
    onRpc("/portal/state_infos/20", () => response);
    await mountAddress();
    expect('[name="state_id"]').toHaveValue("10");
    expect('[name="city_id"]').toHaveValue("100");
    expect('[name="l10n_pe_district"]').toHaveValue("1000");
    const state = queryOne('[name="state_id"]');
    state.value = "20";
    state.dispatchEvent(new Event("change", { bubbles: true }));
    await animationFrame();
    expect('[name="city_id"]').toHaveValue("");
    expect('[name="l10n_pe_district"]').toHaveValue("");
    response.resolve({ cities: [] });
    await animationFrame();
    expect('[name="city_id"] option').toHaveCount(1);
});

test("returning to the same state does not revive its earlier request", async () => {
    const first = new Deferred();
    let calls = 0;
    onRpc("/portal/state_infos/10", () =>
        ++calls === 1 ? first : { cities: [[300, "Current city", "CURRENT"]] },
    );
    onRpc("/portal/state_infos/20", () => ({ cities: [] }));
    const interaction = await mountAddress();
    const pending = interaction.onChangeState();
    await animationFrame();
    queryOne('[name="state_id"]').value = "20";
    await interaction.onChangeState();
    queryOne('[name="state_id"]').value = "10";
    await interaction.onChangeState();
    first.resolve({ cities: [[100, "Obsolete city", "OLD"]] });
    await pending;
    expect('[name="city_id"] option:last-child').toHaveValue("300");
});

test("a failed district lookup clears old selections and allows a retry", async () => {
    let calls = 0;
    onRpc("/portal/city_infos/100", () => {
        if (++calls === 1) {
            throw new Error("district lookup failed");
        }
        return { districts: [[2000, "Current district", "CURRENT"]] };
    });
    const interaction = await mountAddress();
    await expect(interaction.onChangeCity()).rejects.toThrow("district lookup failed");
    expect('[name="l10n_pe_district"] option').toHaveCount(1);
    await interaction.onChangeCity();
    expect('[name="l10n_pe_district"] option:last-child').toHaveValue("2000");
});

test("Save cannot submit obsolete geography while replacement cities are loading", async () => {
    const response = new Deferred();
    onRpc("/portal/state_infos/20", () => response);
    onRpc("/portal/city_infos/200", () => ({
        districts: [[2000, "New district", "NEW"]],
    }));
    const interaction = await mountAddress();
    patchWithCleanup(interaction.http, {
        post: async (url, data) => {
            expect.step("save");
            expect([
                data.get("state_id"),
                data.get("city_id"),
                data.get("l10n_pe_district"),
            ]).toEqual(["20", "200", "2000"]);
            return { invalid_fields: [], messages: [] };
        },
    });
    const state = queryOne('[name="state_id"]');
    state.value = "20";
    state.dispatchEvent(new Event("change", { bubbles: true }));
    queryOne("#save_address").click();
    await animationFrame();
    expect.verifySteps([]);
    response.resolve({ cities: [[200, "New city", "NEW"]] });
    await animationFrame();
    const city = queryOne('[name="city_id"]');
    city.value = "200";
    city.dispatchEvent(new Event("change", { bubbles: true }));
    await animationFrame();
    queryOne('[name="l10n_pe_district"]').value = "2000";
    queryOne("#save_address").click();
    await animationFrame();
    expect.verifySteps(["save"]);
});

test("a country change invalidates outstanding district results even after returning to Peru", async () => {
    const response = new Deferred();
    onRpc("/portal/city_infos/100", () => response);
    const interaction = await mountAddress();
    const pending = interaction.onChangeCity();
    await animationFrame();
    queryOne('[name="country_id"]').value = "2";
    await interaction.onChangeCountry();
    queryOne('[name="country_id"]').value = "1";
    await interaction.onChangeCountry();
    response.resolve({ districts: [[1000, "Obsolete district", "OLD"]] });
    await pending;
    expect('[name="city_id"] option').toHaveCount(1);
    expect('[name="l10n_pe_district"] option').toHaveCount(1);
});
