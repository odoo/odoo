import { expect, test } from "@odoo/hoot";
import {
    contains,
    defineModels,
    mountView,
    onRpc,
    webModels,
} from "@web/../tests/web_test_helpers";
import * as fields from "@web/../tests/_framework/mock_server/mock_fields";
import { Model, ServerModel } from "@web/../tests/_framework/mock_server/mock_model";
import { runAllTimers } from "@odoo/hoot-mock";

class ResCountryState extends ServerModel {
    _name = "res.country.state";

    _records = [
        {
            id: 2,
            display_name: "Brabant Wallon",
        },
    ];
}

class ResCountry extends webModels.ResCountry {
    _records = [
        {
            id: 13,
            display_name: "Belgium",
        },
    ];
}

class ResPartner extends webModels.ResPartner {
    street = fields.Char();
    street2 = fields.Char();
    city = fields.Char();
    zip = fields.Char();
    country_id = fields.Many2one({ relation: "res.country" });
    state_id = fields.Many2one({ relation: "res.country.state" });
}

class OtherModel extends Model {
    _name = "other.model";
    city = fields.Char();
    some_char = fields.Char();
    some_char2 = fields.Char();
    some_char3 = fields.Char();
    m2o = fields.Many2one({ relation: "res.country.state" });
}
defineModels([ResPartner, ResCountryState, ResCountry, OtherModel]);

onRpc("/autocomplete/address", () => ({
    results: [{ formatted_address: "rue des Bourlottes 9, 1367 Ramillies", google_place_id: "1" }],
}));

onRpc("/autocomplete/address_full", () => ({
    country: [13, "Belgium"],
    number: "9",
    city: "Ramillies",
    street: "rue des Bourlottes",
    zip: "1367",
    state: [2, "Brabant Wallon"],
    formatted_street_number: "rue des Bourlottes 9",
    street2: "Ferme 2",
}));

test("correctly fill all standard fields", async () => {
    let googleSessionToken;
    let currentInput;
    onRpc("/autocomplete/address", async (request) => {
        const { params } = await request.json();
        googleSessionToken = params.session_id;
        expect(googleSessionToken).toMatch(/\w+-\w+-\w+-\w+/);
        expect(params.use_employees_key).toBe(true);
        expect(params.partial_address).toBe(currentInput);
        expect.step("/autocomplete/address");
    });
    onRpc("/autocomplete/address_full", async (request) => {
        const { params } = await request.json();
        expect(params.session_id).toBe(googleSessionToken);
        expect(params.use_employees_key).toBe(true);
        expect(params.google_place_id).toBe("1");
        expect.step("/autocomplete/address_full");
    });
    onRpc("/web/dataset/call_kw/res.partner/web_save", async (request) => {
        const { params } = await request.json();
        expect(params.args[1]).toEqual({
            city: "Ramillies",
            country_id: 13,
            state_id: 2,
            // this was input by the user
            // save as is
            street: "odoo farm 3",
            street2: "Ferme 2",
            zip: "1367",
        });
        expect.step("web_save");
    });

    await mountView({
        type: "form",
        resModel: "res.partner",
        arch: `<form>
            <field name="street" widget="google_address_autocomplete"/>
            <field name="street2" />
            <field name="city" />
            <field name="state_id" />
            <field name="zip" />
            <field name="country_id" />
        </form>`,
    });
    currentInput = "odoo farm 2";
    await contains(".o_field_widget[name='street'] input").edit("odoo farm 2", { confirm: false });
    await runAllTimers();
    expect.verifySteps(["/autocomplete/address"]);

    await contains(
        ".o_field_widget[name='street'] .o-autocomplete--dropdown-item a:contains(Bourlottes)"
    ).click();
    expect.verifySteps(["/autocomplete/address_full"]);
    const expectedFields = {
        street: "rue des Bourlottes 9",
        street2: "Ferme 2",
        city: "Ramillies",
        state_id: "Brabant Wallon",
        zip: "1367",
        country_id: "Belgium",
    };
    for (const [field, value] of Object.entries(expectedFields)) {
        expect(`.o_field_widget[name='${field}'] input`).toHaveValue(value);
    }

    const formerToken = googleSessionToken;
    currentInput = "odoo farm 3";
    await contains(".o_field_widget[name='street'] input").edit("odoo farm 3", { confirm: false });
    await runAllTimers();
    expect.verifySteps(["/autocomplete/address"]);
    expect(googleSessionToken).not.toBe(formerToken);

    await contains(".o_form_button_save").click();
    expect.verifySteps(["web_save"]);
});

test("fills current field with values of unknown ones", async () => {
    await mountView({
        type: "form",
        resModel: "other.model",
        arch: `<form>
            <field name="some_char" widget="google_address_autocomplete"/>
            <field name="city" />
        </form>`,
    });

    await contains(".o_field_widget[name='some_char'] input").edit("odoo farm 2", {
        confirm: false,
    });
    await runAllTimers();
    await contains(
        ".o_field_widget[name='some_char'] .o-autocomplete--dropdown-item a:contains(Bourlottes)"
    ).click();

    const expectedFields = {
        some_char: "rue des Bourlottes 9 Ferme 2 Brabant Wallon 1367 Belgium",
        city: "Ramillies",
    };
    for (const [field, value] of Object.entries(expectedFields)) {
        expect(`.o_field_widget[name='${field}'] input`).toHaveValue(value);
    }
});

test("typing in input should make form dirty", async () => {
    onRpc("web_save", ({ args }) => {
        expect.step(args[1])
    });
    await mountView({
        type: "form",
        resModel: "res.partner",
        arch: `<form>
            <field name="street" widget="google_address_autocomplete"/>
        </form>`,
        resId: 1,
    });
    expect(".o_form_button_save:visible").toHaveCount(0);
    await contains(".o_field_widget[name='street'] input").edit("odoo farm 3", { confirm: false });
    await contains(".o_form_button_save:visible").click();
    expect.verifySteps([{street: 'odoo farm 3'}]);
});

test("support field mapping in options", async () => {
    await mountView({
        type: "form",
        resModel: "other.model",
        arch: `<form>
            <field name="some_char" widget="google_address_autocomplete" options="{'state_id': 'm2o', 'zip': 'some_char2', 'city': 'some_char3'}"/>
            <field name="some_char2" />
            <field name="some_char3" />
            <field name="m2o" />
            <field name="city" />
        </form>`,
    });

    await contains(".o_field_widget[name='some_char'] input").edit("odoo farm 2", {
        confirm: false,
    });
    await runAllTimers();
    await contains(
        ".o_field_widget[name='some_char'] .o-autocomplete--dropdown-item a:contains(Bourlottes)"
    ).click();

    const expectedFields = {
        some_char: "rue des Bourlottes 9 Ferme 2 Belgium",
        some_char2: "1367",
        some_char3: "Ramillies",
        m2o: "Brabant Wallon",
    };
    for (const [field, value] of Object.entries(expectedFields)) {
        expect(`.o_field_widget[name='${field}'] input`).toHaveValue(value);
    }
});
