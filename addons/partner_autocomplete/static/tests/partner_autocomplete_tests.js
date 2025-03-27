/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import {
    click,
    editInput,
    editSelect,
    getFixture,
    patchWithCleanup,
    triggerEvent,
} from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { loadJS } from "@web/core/assets";

let target;

async function editInputNoChangeEvent(input, value) {
    // Note: we can't use editInput as it triggers the 'change' event which will close the autocomplete dropdown
    input.value = value;
    await triggerEvent(input, null, "input");
}


const iapSuggestions = [
    {
        "name": "First Company",
        "duns": "123",
        "city": "FirstCity",
        "country_id": {"id": 1, "display_name": "Belgium"},
    },
    {
        "name": "Second Company",
        "duns": "456",
        "city": "SecondCity",
        "country_id": {"id": 1, "display_name": "Belgium"},
    },
    {
        "name": "Third Company",
        "duns": "789",
        "city": "ThirdCity",
        "country_id": {"id": 1, "display_name": "Belgium"},
    },
];

const clearbitSuggestions = [
    {
        "name": "First Company",
        "domain": "firstcompany.com",
    },
    {
        "name": "MyCompany",
        "domain": "mycompany.com",
    },
    {
        "name": "YourCompany",
        "domain": "yourcompany.com",
    },
];


QUnit.module('partner_autocomplete', {
    async before() {
        // Load the lib before the tests to prevent them from
        // failing because of the delay.
        await loadJS("/partner_autocomplete/static/lib/jsvat.js");
    },
    beforeEach() {
        target = getFixture();

        // Make autocomplete input instantaneous
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
        });

        setupViewRegistries();
    },
}, function () {

    const makeViewParams = {
        serverData: {
            models: {
                'res.partner': {
                    fields: {
                        company_type: {
                            string: "Company Type",
                            type: "selection",
                            selection: [["company", "Company"], ["individual", "Individual"]],
                            searchable: true
                        },
                        name: {string: "Name", type: "char", searchable: true},
                        parent_id: {string: "Company", type: "many2one", relation: "res.partner", searchable: true},
                        website: {string: "Website", type: "char", searchable: true},
                        email: {string: "Email", type: "char", searchable: true},
                        image_1920: {string: "Image", type: "binary", searchable: true},
                        phone: {string: "Phone", type: "char", searchable: true},
                        street: {string: "Street", type: "char", searchable: true},
                        street2: {string: "Street2", type: "char", searchable: true},
                        city: {string: "City", type: "char", searchable: true},
                        zip: {string: "Zip", type: "char", searchable: true},
                        state_id: {string: "State", type: "many2one", relation: "res.country.state", searchable: true},
                        country_id: {string: "Country", type: "many2one", relation: "res.country", searchable: true},
                        comment: {string: "Comment", type: "char", searchable: true},
                        vat: {string: "Vat", type: "char", searchable: true},
                        is_company: {string: "Is company", type: "bool", searchable: true},
                    },
                    records: [],
                    onchanges: {
                        company_type: (obj) => {
                            obj.is_company = obj.company_type === 'company';
                        },
                    },
                },
                'res.country': {
                    fields: {
                        display_name: {string: "Name", type: "char", searchable: true},
                    },
                    records: [{
                        id: 1,
                        display_name: 'Belgium',
                    }],
                },
                'res.country.state': {
                    fields: {
                        name: {string: "Name", type: "char", searchable: true},
                    },
                    records: [{
                        id: 1,
                        name: 'Walloon Brabant',
                    }],
                },
            },
        },
        resModel: "res.partner",
        type: "form",
        arch:
            `<form>
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
            </form>`,
        async mockRPC(route, args) {
            if (route === "/web/dataset/call_kw/res.partner/autocomplete_by_name" || route === "/web/dataset/call_kw/res.partner/autocomplete_by_vat") {
                return Promise.resolve(iapSuggestions);
            }
            else if (route === "/web/dataset/call_kw/res.partner/enrich_by_duns") {
                return Promise.resolve({
                    "name": iapSuggestions.filter((sugg) => sugg.duns === args.args[0])[0].name,
                    "vat": "BE0477472701",
                    "duns": "372441183",
                    "city": "Ramillies",
                    "zip": "1367",
                    "street": "Chaussée de Namur 40",
                    "street2": false,
                    "email": "hello@odoo.com",
                    "phone": "3281813700",
                    "website": "www.odoo.com",
                    "domain": "odoo.com",
                    "country_id": {
                        "id": 1,
                        "name": "Belgium"
                    },
                    "state_id": {
                        "id": 1,
                        "name": "Walloon Brabant"
                    },
                });
            }
            else if (route.startsWith("https://autocomplete.clearbit.com/v1/companies/suggest")) {
                return Promise.resolve(clearbitSuggestions)
            }
        }
    }

    QUnit.test("Partner autocomplete : Company type = Individual", async function (assert) {
        assert.expect(12);
        await makeView(makeViewParams);

        // Set company type to Individual
        await editSelect(target, "[name='company_type'] > select", '"individual"');

        const nameInput = target.querySelector("[name='name'] input");
        assert.doesNotHaveClass(nameInput, 'o-autocomplete--input', "The input for field 'name' should be a regular input");

        const companyInput = target.querySelector("[name='parent_id'] input");
        const autocompleteContainer = companyInput.parentElement;

        await click(companyInput, null);
        assert.containsNone(
            autocompleteContainer,
            ".o-autocomplete--dropdown-item.partner_autocomplete_dropdown_many2one",
            "There should be no option when input is empty"
        );

        await editInputNoChangeEvent(companyInput, "od");
        assert.containsNone(
            autocompleteContainer,
            ".o-autocomplete--dropdown-item.partner_autocomplete_dropdown_many2one",
            "There should be no option when the length of the query is < 3"
        );

        await editInputNoChangeEvent(companyInput, "company");
        assert.containsN(
            autocompleteContainer,
            ".o-autocomplete--dropdown-item.partner_autocomplete_dropdown_many2one",
            3,
            "Odoo autocomplete options should be shown"
        );

        // Click on the first option - "First company"
        await click(autocompleteContainer.querySelectorAll('ul li.partner_autocomplete_dropdown_many2one')[0], null);

        const modalContent = target.querySelector('.modal-content');
        // Check that the fields of the modal have been pre-filled
        const expectedValues = {
            "name": "First Company",
            "vat": "BE0477472701",
            "street": "Chaussée de Namur 40",
            "city": "Ramillies",
            "zip": "1367",
            "phone": "3281813700",
            "country_id": "Belgium",
            "state_id": "Walloon Brabant",
        };
        for (const [fieldName, expectedValue] of Object.entries(expectedValues)) {
            assert.strictEqual(modalContent.querySelector(`[name=${fieldName}] input`).value, expectedValue, `${fieldName} should be pre-filled`);
        }
    });

    QUnit.test("Partner autocomplete : Company type = Company / Name search", async function (assert) {
        assert.expect(11);
        await makeView(makeViewParams);

        // Set company type to Company
        await editSelect(target, "[name='company_type'] > select", '"company"');

        const input = target.querySelector("[name='name'] .dropdown input");
        const autocompleteContainer = input.parentElement;

        await click(input, null);
        assert.containsNone(
            autocompleteContainer,
            ".o-autocomplete--dropdown-item.partner_autocomplete_dropdown_many2one",
            "There should be no option when input is empty"
        );

        await editInputNoChangeEvent(input, "od");
        assert.containsNone(
            autocompleteContainer,
            ".o-autocomplete--dropdown-item.partner_autocomplete_dropdown_many2one",
            "There should be no option when the length of the query is < 3"
        );

        await editInputNoChangeEvent(input, "company");
        assert.containsN(
            autocompleteContainer,
            ".o-autocomplete--dropdown-item",
            4,  // 3 options + 1 for the worldwide option
            "Odoo autocomplete options should be shown"
        );

        // Click on the first option - "First Company"
        await click(autocompleteContainer.querySelectorAll('ul li')[0], null);

        // Check that the fields have been filled
        const expectedValues = {
            "name": "First Company",
            "vat": "BE0477472701",
            "street": "Chaussée de Namur 40",
            "city": "Ramillies",
            "zip": "1367",
            "phone": "3281813700",
            "country_id": "Belgium",
            "state_id": "Walloon Brabant",
        };
        for (const [fieldName, expectedValue] of Object.entries(expectedValues)) {
            assert.strictEqual(target.querySelector(`[name=${fieldName}] input`).value, expectedValue, `${fieldName} should be filled`);
        }
    });

    QUnit.test("Partner autocomplete : Company type = Company / VAT search", async function (assert) {
        assert.expect(11);

        await makeView(makeViewParams);

        // Set company type to Company
        await editSelect(target, "[name='company_type'] > select", '"company"');

        const input = target.querySelector("[name='vat'] .dropdown input");
        const autocompleteContainer = input.parentElement;

        await click(input, null);
        assert.containsNone(
            autocompleteContainer,
            ".o-autocomplete--dropdown-item.partner_autocomplete_dropdown_many2one",
            "There should be no option when input is empty"
        );

        await editInputNoChangeEvent(input, "blabla");
        assert.containsNone(
            autocompleteContainer,
            ".o-autocomplete--dropdown-item.partner_autocomplete_dropdown_many2one",
            "There should be no option when the value doesn't have a valid VAT number format"
        );

        await editInputNoChangeEvent(input, "BE0477472701");
        assert.containsN(
            autocompleteContainer,
            ".o-autocomplete--dropdown-item",
            4,  // 3 options + 1 for the worldwide option
            "Odoo read_by_vat options should be shown"
        );

        // Click on the first option - "First company"
        await click(autocompleteContainer.querySelectorAll('ul li')[0], null);

        // Check that the fields have been filled
        const expectedValues = {
            "name": "First Company",
            "vat": "BE0477472701",
            "street": "Chaussée de Namur 40",
            "city": "Ramillies",
            "zip": "1367",
            "phone": "3281813700",
            "country_id": "Belgium",
            "state_id": "Walloon Brabant",
        };
        for (const [fieldName, expectedValue] of Object.entries(expectedValues)) {
            assert.strictEqual(target.querySelector(`[name=${fieldName}] input`).value, expectedValue, `${fieldName} should be filled`);
        }
    });

    QUnit.test("Click out after edition", async function (assert) {
        assert.expect(2);
        await makeView(makeViewParams);
        const input = target.querySelector("[name=parent_id] input.o-autocomplete--input.o_input");
        await triggerEvent(input, null, "focus");
        await click(input);
        await editInput(input, null, "go");
        assert.strictEqual(input.value, "go");
        await triggerEvent(target, null, "pointerdown");
        await triggerEvent(input, null, "blur");
        assert.strictEqual(input.value, "");
    });

    QUnit.test("Can unset the partner many2one field", async function (assert) {
        assert.expect(5);
        const record = { id: 1, name: "Some partner", parent_id: 1 };
        makeViewParams.serverData.models["res.partner"].records.push(record);
        makeViewParams.resId = 1;
        const mockRPC = makeViewParams.mockRPC;
        makeViewParams.mockRPC = function(route, { args, method }) {
            if (method === "web_save") {
                assert.step("web_save");
                assert.deepEqual(args[1].parent_id, false);
            }
            return mockRPC(...arguments);
        }
        await makeView(makeViewParams);
        assert.strictEqual(target.querySelector("[name=parent_id] input").value, "Some partner");
        const input = target.querySelector("[name=parent_id] input.o-autocomplete--input.o_input");
        await triggerEvent(input, null, "focus");
        await click(input);
        await editInput(target.querySelector("[name=parent_id] input.o-autocomplete--input.o_input"), null, "");
        assert.isVisible(target, ".o_form_button_save");
        await click(target.querySelector(".o_form_button_save"));
        assert.verifySteps(["web_save"]);
    });

    QUnit.test("Hide auto complete suggestion for no create", async function (assert) {
        const partnerMakeViewParams = {
            ...makeViewParams,
            arch:
                `<form>
                    <field name="company_type"/>
                    <field name="parent_id" widget="res_partner_many2one" options="{'no_create': True}"/>
                </form>`
        }
        await makeView(partnerMakeViewParams);
        const input = target.querySelector("[name='parent_id'] input");
        await editInputNoChangeEvent(input, "blabla");
        const autocompleteContainer = input.parentElement;
        assert.containsNone(
            autocompleteContainer,
            ".o-autocomplete--dropdown-item.partner_autocomplete_dropdown_many2one",
            "There should be no option when partner field has no_create attribute"
        );
    });

    QUnit.test("Display auto complete suggestion for canCreate", async function (assert) {
        assert.expect(1);
        const partnerMakeViewParams = {
            ...makeViewParams,
            arch:
                `<form>
                    <field name="company_type"/>
                    <field name="parent_id" widget="res_partner_many2one" options="{'no_create': False}"/>
                </form>`
        }
        await makeView(partnerMakeViewParams);
        const input = target.querySelector("[name='parent_id'] input");
        await editInputNoChangeEvent(input, "blabla");
        const autocompleteContainer = input.parentElement;
        assert.containsN(
            autocompleteContainer,
            ".o-autocomplete--dropdown-item",
            6,  //3 suggestions + create + create & edit + search worldwide
            "Odoo autocomplete options should be shown"
        );
    });

    QUnit.test("Partner autocomplete : onChange should not disturb option selection", async function (assert) {
        await makeView(makeViewParams);

        // Set company type to Company
        await editSelect(target, "[name='company_type'] > select", '"company"');

        const input = target.querySelector("[name='name'] .dropdown input");
        const autocompleteContainer = input.parentElement;

        await click(input, null);
        await editInputNoChangeEvent(input, "company");
        assert.containsN(
            autocompleteContainer,
            ".o-autocomplete--dropdown-item",
            4,  // 3 options + 1 for the worldwide option
            "Odoo autocomplete options should be shown"
        );
        // Click on the second option (include realistic events) - "Second company"
        await triggerEvent(
            target.querySelectorAll(".o-autocomplete--dropdown-item")[1],
            "",
            "pointerdown"
        );
        await triggerEvent(
            target.querySelectorAll(".o-autocomplete--dropdown-item")[1],
            "",
            "mousedown"
        );
        await triggerEvent(input, "", "change");
        await triggerEvent(input, "", "blur");
        await click(target.querySelectorAll(".o-autocomplete--dropdown-item")[1], "");

        // Check that the fields have been filled
        const expectedValues = {
            "name": "Second Company",
            "vat": "BE0477472701",
            "street": "Chaussée de Namur 40",
            "city": "Ramillies",
            "zip": "1367",
            "phone": "3281813700",
            "country_id": "Belgium",
            "state_id": "Walloon Brabant",
        };
        for (const [fieldName, expectedValue] of Object.entries(expectedValues)) {
            assert.strictEqual(target.querySelector(`[name=${fieldName}] input`).value, expectedValue, `${fieldName} should be filled`);
        }
    });
});
