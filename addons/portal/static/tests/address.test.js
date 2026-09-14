import { expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { CustomerAddress } from "@portal/interactions/address";
import { getInteraction, startInteraction } from "@web/../tests/public/helpers";
import { onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { Deferred } from "@web/core/utils/concurrency";

const address = `<div class="o_customer_address_fill"><div id="errors"></div>
    <form class="address_autoformat" data-submit-url="/my/address/submit">
        <input name="address_type" value="billing"/><input name="required_fields" value=""/>
        <select name="country_id"><option value="">Choose</option><option value="1">One</option><option value="2">Two</option></select>
        <div><select name="state_id"><option value="">Choose</option><option value="10" selected="selected">Old state</option></select></div>
        <input name="phone"/><button id="save_address" type="button">Save</button>
    </form></div>`;
const country = (phoneCode, states = []) => ({
    phone_code: phoneCode,
    states,
    state_required: false,
    required_fields: [],
});

test("a late country response cannot replace the selected country's fields", async () => {
    const first = new Deferred();
    onRpc("/my/address/country_info/1", () => first);
    onRpc("/my/address/country_info/2", () => country(22));
    const { core } = await startInteraction(CustomerAddress, address);
    const interaction = getInteraction(core, CustomerAddress);
    queryOne('[name="country_id"]').value = "1";
    const pending = interaction.onChangeCountry();
    queryOne('[name="country_id"]').value = "2";
    await interaction.onChangeCountry();
    first.resolve(country(11, [[10, "Old state", "OLD"]]));
    await pending;
    expect('[name="phone"]').toHaveAttribute("placeholder", "+22");
    expect('[name="state_id"] option').toHaveCount(1);
    expect(queryOne('[name="state_id"]').value).toBe("");
});

test("clearing the country invalidates an outstanding response", async () => {
    const response = new Deferred();
    onRpc("/my/address/country_info/1", () => response);
    const { core } = await startInteraction(CustomerAddress, address);
    const interaction = getInteraction(core, CustomerAddress);
    queryOne('[name="country_id"]').value = "1";
    const pending = interaction.onChangeCountry();
    queryOne('[name="country_id"]').value = "";
    response.resolve(country(11));
    await pending;
    expect(queryOne('[name="phone"]').placeholder).toBe("");
});

test("form submission and checkout calls share one pending save", async () => {
    const { core } = await startInteraction(CustomerAddress, address);
    const interaction = getInteraction(core, CustomerAddress);
    const response = new Deferred();
    patchWithCleanup(interaction.http, {
        post: async () => {
            expect.step("save");
            return response;
        },
    });
    const submit = new Event("submit", { bubbles: true, cancelable: true });
    queryOne("form").dispatchEvent(submit);
    expect(submit.defaultPrevented).toBe(true);
    const duplicate = interaction.saveAddress(new Event("click"));
    await animationFrame();
    expect.verifySteps(["save"]);
    response.resolve({ invalid_fields: [], messages: [] });
    await duplicate;
});

test("saving after a country change waits for its state choices", async () => {
    const response = new Deferred();
    onRpc("/my/address/country_info/2", () => response);
    const { core } = await startInteraction(CustomerAddress, address);
    const interaction = getInteraction(core, CustomerAddress);
    patchWithCleanup(interaction.http, {
        post: async (url, data) => {
            expect.step("save");
            expect(data.get("state_id")).toBe("");
            return { invalid_fields: [], messages: [] };
        },
    });
    const select = queryOne('[name="country_id"]');
    select.value = "2";
    select.dispatchEvent(new Event("change", { bubbles: true }));
    const saving = interaction.saveAddress(new Event("click"));
    await animationFrame();
    expect.verifySteps([]);
    response.resolve(country(22));
    await saving;
    expect.verifySteps(["save"]);
});

test("saving retries country metadata after a failed lookup", async () => {
    let calls = 0;
    onRpc("/my/address/country_info/2", () => {
        if (++calls === 1) {
            throw new Error("country lookup failed");
        }
        return country(22);
    });
    const { core } = await startInteraction(CustomerAddress, address);
    const interaction = getInteraction(core, CustomerAddress);
    patchWithCleanup(interaction.http, {
        post: async (url, data) => {
            expect.step("save");
            expect(data.get("state_id")).toBe("");
            return { invalid_fields: [], messages: [] };
        },
    });
    queryOne('[name="country_id"]').value = "2";
    await expect(interaction.onChangeCountry()).rejects.toThrow(
        "country lookup failed",
    );
    const outcome = await interaction.saveAddress(new Event("click")).then(
        () => "saved",
        () => "failed",
    );
    expect(outcome).toBe("saved");
    expect(calls).toBe(2);
    expect.verifySteps(["save"]);
});

test("an obsolete failed lookup cannot abort a save waiting for the new country", async () => {
    const first = new Deferred();
    onRpc("/my/address/country_info/1", () => first);
    onRpc("/my/address/country_info/2", () => country(22));
    const { core } = await startInteraction(CustomerAddress, address);
    const interaction = getInteraction(core, CustomerAddress);
    patchWithCleanup(interaction.http, {
        post: async () => ({ invalid_fields: [], messages: [] }),
    });
    queryOne('[name="country_id"]').value = "1";
    const oldLookup = interaction.onChangeCountry().catch(() => {});
    const saving = interaction.saveAddress(new Event("click")).then(
        () => "saved",
        () => "failed",
    );
    queryOne('[name="country_id"]').value = "2";
    await interaction.onChangeCountry();
    first.reject(new Error("obsolete lookup failed"));
    await oldLookup;
    expect(await saving).toBe("saved");
});

test("an initial metadata failure leaves the Save click able to retry", async () => {
    expect.errors(1);
    let calls = 0;
    onRpc("/my/address/country_info/2", () => {
        if (++calls === 1) {
            throw new Error("initial country lookup failed");
        }
        return country(22);
    });
    const { core } = await startInteraction(
        CustomerAddress,
        address.replace('<option value="2">', '<option value="2" selected="selected">'),
    );
    await animationFrame();
    expect.verifyErrors([/initial country lookup failed/]);
    const interaction = getInteraction(core, CustomerAddress);
    patchWithCleanup(interaction.http, {
        post: async () => {
            expect.step("saved");
            return { invalid_fields: [], messages: [] };
        },
    });
    queryOne("#save_address").click();
    await animationFrame();
    expect(calls).toBe(2);
    expect.verifySteps(["saved"]);
});
