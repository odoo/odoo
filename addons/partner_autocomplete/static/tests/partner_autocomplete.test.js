import { mailModels } from "@mail/../tests/mail_test_helpers";
import { expect, getFixture, test } from "@odoo/hoot";
import { advanceTime, queryOne } from "@odoo/hoot-dom";
import {
    contains,
    defineModels,
    editSelectMenu,
    fields,
    models,
    mountView,
    onRpc,
    preloadBundle,
} from "@web/../tests/web_test_helpers";

// Autocomplete has a debounce time of 250 ms on input
async function editAutocomplete(el, value) {
    await contains(el).edit(value, { confirm: false });
    await advanceTime(250);
}

class ResPartner extends mailModels.ResPartner {
    company_type = fields.Selection({
        string: "Company Type",
        type: "selection",
        selection: [
            ["company", "Company"],
            ["individual", "Individual"],
        ],
        onChange: (obj) => {
            obj.is_company = obj.company_type === "company";
        },
    });
    state_id = fields.Many2one({ relation: "res.country.state" });
    _views = {
        form: `
            <form>
                <field name="company_type"/>
                <field name="name" widget="field_partner_autocomplete"/>
                <field name="parent_id" widget="res_partner_many2one"/>
                <field name="website"/>
                <field name="image_1920" widget="image"/>
                <field name="email"/>
                <field name="phone"/>
                <field name="street"/>
                <field name="street2"/>
                <field name="city"/>
                <field name="state_id"/>
                <field name="zip"/>
                <field name="country_id"/>
                <field name="vat" widget="field_partner_autocomplete"/>
            </form>
        `,
    };
}

class ResCountry extends models.Model {
    _name = "res.country";
    name = fields.Char();
    _records = [
        {
            id: 1,
            name: "Belgium",
        },
    ];
}

class ResCountryState extends models.Model {
    _name = "res.country.state";
    name = fields.Char();
    _records = [
        {
            id: 1,
            name: "Walloon Brabant",
        },
    ];
}

defineModels({ ...mailModels, ResPartner, ResCountry, ResCountryState });

const iapSuggestions = [
    {
        name: "First Company",
        duns: "123",
        city: "FirstCity",
        country_id: { id: 1, name: "Belgium" },
    },
    {
        name: "Second Company",
        duns: "456",
        city: "SecondCity",
        country_id: { id: 1, name: "Belgium" },
    },
    {
        name: "Third Company",
        duns: "789",
        city: "ThirdCity",
        country_id: { id: 1, name: "Belgium" },
    },
];

const clearbitSuggestions = [
    {
        name: "First Company",
        domain: "firstcompany.com",
    },
    {
        name: "MyCompany",
        domain: "mycompany.com",
    },
    {
        name: "YourCompany",
        domain: "yourcompany.com",
    },
];

onRpc("res.partner", "autocomplete_by_name", () => iapSuggestions);
onRpc("res.partner", "autocomplete_by_vat", () => iapSuggestions);
onRpc("res.partner", "enrich_by_duns", ({ args }) => ({
    name: iapSuggestions.filter((sugg) => sugg.duns === args[0])[0].name,
    vat: "BE0477472701",
    duns: "372441183",
    city: "Ramillies",
    zip: "1367",
    street: "Chaussée de Namur 40",
    street2: false,
    email: "hello@odoo.com",
    phone: "3281813700",
    website: "www.odoo.com",
    domain: "odoo.com",
    country_id: {
        id: 1,
        name: "Belgium",
    },
    state_id: {
        id: 1,
        name: "Walloon Brabant",
    },
}));
onRpc("/v1/companies/suggest", () => clearbitSuggestions);

preloadBundle("web.jsvat_lib");

test.tags("desktop");
test("Partner autocomplete : Company type = Individual", async () => {
    await mountView({
        resModel: "res.partner",
        type: "form",
    });

    await editSelectMenu("[name='company_type'] input", {
        value: "Individual",
    });
    expect("[name='name'] input").not.toHaveClass("o-autocomplete--input", {
        message: "The input for field 'name' should be a regular input",
    });

    await contains("[name='parent_id']:first input").click();
    expect(
        "[name='parent_id']:first .o-autocomplete .o-autocomplete--dropdown-item.partner_autocomplete_dropdown_many2one"
    ).toHaveCount(0, { message: "There should be no option when input is empty" });

    await editAutocomplete("[name='parent_id']:first input", "od");
    expect(
        "[name='parent_id']:first .o-autocomplete .o-autocomplete--dropdown-item.partner_autocomplete_dropdown_many2one"
    ).toHaveCount(0, { message: "There should be no option when the length of the query is < 3" });

    await editAutocomplete("[name='parent_id']:first input", "company");
    expect(
        "[name='parent_id']:first .o-autocomplete .o-autocomplete--dropdown-item.partner_autocomplete_dropdown_many2one"
    ).toHaveCount(3);

    // Click on the first option - "First company"
    await contains(
        "[name='parent_id']:first .o-autocomplete ul li.partner_autocomplete_dropdown_many2one:first"
    ).click();
    // Check that the fields of the modal have been pre-filled
    const expectedValues = {
        name: "First Company",
        vat: "BE0477472701",
        street: "Chaussée de Namur 40",
        city: "Ramillies",
        zip: "1367",
        phone: "3281813700",
        country_id: "Belgium",
        state_id: "Walloon Brabant",
    };
    for (const [fieldName, expectedValue] of Object.entries(expectedValues)) {
        expect(`.modal-content [name=${fieldName}] input`).toHaveValue(expectedValue, {
            message: `${fieldName} should be pre-filled`,
        });
    }
});

test("Partner autocomplete : Company type = Company / Name search", async () => {
    expect.assertions(11);
    await mountView({
        resModel: "res.partner",
        type: "form",
    });

    await editSelectMenu("[name='company_type'] input", {
        value: "Company",
    });
    await contains("[name='name'] .dropdown input").click();
    expect(
        "[name='name'] .o-autocomplete .o-autocomplete--dropdown-item.partner_autocomplete_dropdown_many2one"
    ).toHaveCount(0, { message: "There should be no option when input is empty" });

    await editAutocomplete("[name='name'] .dropdown input", "od");
    expect(
        "[name='name'] .o-autocomplete .o-autocomplete--dropdown-item.partner_autocomplete_dropdown_many2one"
    ).toHaveCount(0, { message: "There should be no option when the length of the query is < 3" });

    await editAutocomplete("[name='name'] .dropdown input", "company");
    // 3 options + 1 for the worldwide option
    expect("[name='name'] .o-autocomplete .o-autocomplete--dropdown-item").toHaveCount(4);

    // Click on the first option - "First Company"
    await contains("[name='name'] .o-autocomplete ul li").click();

    // Check that the fields have been filled
    const expectedValues = {
        name: "First Company",
        vat: "BE0477472701",
        street: "Chaussée de Namur 40",
        city: "Ramillies",
        zip: "1367",
        phone: "3281813700",
        country_id: "Belgium",
        state_id: "Walloon Brabant",
    };
    for (const [fieldName, expectedValue] of Object.entries(expectedValues)) {
        expect(`[name=${fieldName}] input`).toHaveValue(expectedValue, {
            message: `${fieldName} should be filled`,
        });
    }
});

test("Partner autocomplete : Company type = Company / VAT search", async () => {
    expect.assertions(11);

    await mountView({
        resModel: "res.partner",
        type: "form",
    });

    await editSelectMenu("[name='company_type'] input", {
        value: "Company",
    });
    await contains("[name='vat'] .dropdown input").click();
    expect(
        "[name='vat'] .o-autocomplete .o-autocomplete--dropdown-item.partner_autocomplete_dropdown_many2one"
    ).toHaveCount(0, { message: "There should be no option when input is empty" });

    await editAutocomplete("[name='vat'] .dropdown input", "blabla");
    expect(
        "[name='vat'] .o-autocomplete .o-autocomplete--dropdown-item.partner_autocomplete_dropdown_many2one"
    ).toHaveCount(0, {
        message: "There should be no option when the value doesn't have a valid VAT number format",
    });

    await editAutocomplete("[name='vat'] .dropdown input", "BE0477472701");
    // 3 options + 1 for the worldwide option
    expect("[name='vat'] .o-autocomplete .o-autocomplete--dropdown-item").toHaveCount(4);

    // Click on the first option - "First company"
    await contains("[name='vat'] .o-autocomplete ul li").click();

    // Check that the fields have been filled
    const expectedValues = {
        name: "First Company",
        vat: "BE0477472701",
        street: "Chaussée de Namur 40",
        city: "Ramillies",
        zip: "1367",
        phone: "3281813700",
        country_id: "Belgium",
        state_id: "Walloon Brabant",
    };
    for (const [fieldName, expectedValue] of Object.entries(expectedValues)) {
        expect(`[name=${fieldName}] input`).toHaveValue(expectedValue, {
            message: `${fieldName} should be filled`,
        });
    }
});

test.tags("desktop");
test("Click out after edition", async () => {
    expect.assertions(2);
    await mountView({
        resModel: "res.partner",
        type: "form",
    });
    const input = queryOne("[name=parent_id] input.o-autocomplete--input.o_input");
    await contains(input).click();
    await editAutocomplete(input, "go");
    expect(input).toHaveValue("go");
    await contains(getFixture()).click();
    expect(input).toHaveValue("");
});

test.tags("desktop");
test("Can unset the partner many2one field", async () => {
    ResPartner._records[0] = { id: 1, name: "Some partner", parent_id: 1 };
    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        expect(args[1].parent_id).toBe(false);
    });
    await mountView({
        resModel: "res.partner",
        type: "form",
        resId: 1,
    });
    expect("[name=parent_id] input").toHaveValue("Some partner");
    await contains("[name=parent_id] input.o-autocomplete--input.o_input").clear({
        confirm: false,
    });
    await contains(getFixture()).click();
    expect(".o_form_button_save").toBeVisible();
    await contains(".o_form_button_save").click();
    expect.verifySteps(["web_save"]);
});

test("Hide auto complete suggestion for no create", async () => {
    await mountView({
        resModel: "res.partner",
        type: "form",
        arch: `<form>
            <field name="company_type"/>
            <field name="parent_id" widget="res_partner_many2one" options="{'no_create': True}"/>
        </form>`,
    });
    await editAutocomplete("[name='parent_id'] input", "blabla");
    expect(
        "[name='parent_id'] .o-autocomplete .o-autocomplete--dropdown-item.partner_autocomplete_dropdown_many2one"
    ).toHaveCount(0, {
        message: "There should be no option when partner field has no_create attribute",
    });
});

test.tags("desktop");
test("Display auto complete suggestion for canCreate", async () => {
    await mountView({
        resModel: "res.partner",
        type: "form",
        arch: `<form>
            <field name="company_type"/>
            <field name="parent_id" widget="res_partner_many2one" options="{'no_create': False}"/>
        </form>`,
    });
    await editAutocomplete("[name='parent_id'] input", "blabla");
    // create + create & edit + 3 partner suggestions + search worldwide
    expect("[name='parent_id'] .o-autocomplete .o-autocomplete--dropdown-item").toHaveCount(6);
});

test("Partner autocomplete : onChange should not disturb option selection", async () => {
    await mountView({
        resModel: "res.partner",
        type: "form",
    });

    await editSelectMenu("[name='company_type'] input", {
        value: "Company",
    });
    await contains("[name='name'] .dropdown input").click();
    await editAutocomplete("[name='name'] .dropdown input", "company");
    // 3 options + 1 for the worldwide option
    expect("[name='name'] .o-autocomplete .o-autocomplete--dropdown-item").toHaveCount(4);
    await contains(".o-autocomplete--dropdown-item:eq(1)").click();

    // Check that the fields have been filled
    const expectedValues = {
        name: "Second Company",
        vat: "BE0477472701",
        street: "Chaussée de Namur 40",
        city: "Ramillies",
        zip: "1367",
        phone: "3281813700",
        country_id: "Belgium",
        state_id: "Walloon Brabant",
    };
    for (const [fieldName, expectedValue] of Object.entries(expectedValues)) {
        expect(`[name=${fieldName}] input`).toHaveValue(expectedValue, {
            message: `${fieldName} should be filled`,
        });
    }
});
