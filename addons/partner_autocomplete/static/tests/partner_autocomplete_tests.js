/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
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

const serviceRegistry = registry.category("services");

let target;

async function editInputNoChangeEvent(input, value) {
    // Note: we can't use editInput as it triggers the 'change' event which will close the autocomplete dropdown
    input.value = value;
    await triggerEvent(input, null, "input");
}

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
        const fakeHTTPService = {
            start() {
                return {
                    get: (route) => {
                        return Promise.resolve([
                            {
                                "name": "Odoo",
                                "domain": "odoo.com",
                            },
                            {
                                "name": "MyCompany",
                                "domain": "mycompany.com",
                            },
                            {
                                "name": "YourCompany",
                                "domain": "yourcompany.com",
                            },
                        ]);
                    },
                };
            },
        };
        serviceRegistry.add("http", fakeHTTPService);
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
                        image_1920: {string: "Image", type: "binary", searchable: true},
                        phone: {string: "Phone", type: "char", searchable: true},
                        street: {string: "Street", type: "char", searchable: true},
                        city: {string: "City", type: "char", searchable: true},
                        zip: {string: "Zip", type: "char", searchable: true},
                        state_id: {string: "State", type: "many2one", relation: "res.country.state", searchable: true},
                        country_id: {string: "Country", type: "many2one", relation: "res.country", searchable: true},
                        comment: {string: "Comment", type: "char", searchable: true},
                        vat: {string: "Vat", type: "char", searchable: true},
                        is_company: {string: "Is company", type: "bool", searchable: true},
                        partner_gid: {string: "Company data ID", type: "integer", searchable: true},
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
                        name: 'United States',
                    }],
                },
                'res.country.state': {
                    fields: {
                        display_name: {string: "Name", type: "char", searchable: true},
                    },
                    records: [{
                        id: 1,
                        name: 'California (US)',
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
                <field name="phone"/>
                <field name="street"/>
                <field name="city"/>
                <field name="state_id"/>
                <field name="zip"/>
                <field name="country_id"/>
                <field name="comment"/>
                <field name="vat" widget="field_partner_autocomplete"/>
            </form>`,
        async mockRPC(route, args) {
            if (route === "/web/dataset/call_kw/res.partner/autocomplete" || route === "/web/dataset/call_kw/res.partner/read_by_vat") {
                return Promise.resolve([
                    {
                        "partner_gid": 1,
                        "website": "firstcompany.com",
                        "name": "First company",
                        "ignored": false,
                        "vat": ""
                    },
                    {
                        "partner_gid": 2,
                        "website": "secondcompany.com",
                        "name": "Second company",
                        "ignored": false,
                        "vat": ""
                    },
                    {
                        "partner_gid": 3,
                        "website": "thirdcompany.com",
                        "name": "Third company",
                        "ignored": false,
                        "vat": ""
                    },
                ]);
            }
            else if (route === "/web/dataset/call_kw/res.partner/enrich_company") {
                return Promise.resolve({
                    "partner_gid": args.args[1],
                    "website": args.args[0],
                    "name": args.args[1] === 1 ? "First company" : "Second company",
                    'logo': false,
                    "ignored": false,
                    "vat": "Some VAT number",
                    "street": "Some street",
                    "city": "Some city",
                    "zip": "1234",
                    "phone": "+0123456789",
                    "email": "info@firstcompany.com",
                    "country_id": {
                        'id': 1,
                        'display_name': "United States",
                    },
                    "state_id": {
                        'id': 1,
                        'display_name': "California (US)",
                    },
                });
            }
        }
    }

    QUnit.test("Partner autocomplete : Company type = Individual", async function (assert) {
        assert.expect(13);
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
            6,
            "Clearbit and Odoo autocomplete options should be shown"
        );

        // Click on the first option - "First company"
        await click(autocompleteContainer.querySelectorAll('ul li.partner_autocomplete_dropdown_many2one')[0], null);

        const modalContent = target.querySelector('.modal-content');
        // Check that the fields of the modal have been pre-filled
        const expectedValues = {
            "website": "firstcompany.com",
            "name": "First company",
            "vat": "Some VAT number",
            "street": "Some street",
            "city": "Some city",
            "zip": "1234",
            "phone": "+0123456789",
            "country_id": "United States",
            "state_id": "California (US)",
        };
        for (const [fieldName, expectedValue] of Object.entries(expectedValues)) {
            assert.strictEqual(modalContent.querySelector(`[name=${fieldName}] input`).value, expectedValue, `${fieldName} should be pre-filled`);
        }
    });

    QUnit.test("Partner autocomplete : Company type = Company / Name search", async function (assert) {
        assert.expect(12);
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
            6,
            "Clearbit and Odoo autocomplete options should be shown"
        );

        // Click on the first option - "First company"
        await click(autocompleteContainer.querySelectorAll('ul li')[0], null);

        // Check that the fields have been filled
        const expectedValues = {
            "website": "firstcompany.com",
            "name": "First company",
            "vat": "Some VAT number",
            "street": "Some street",
            "city": "Some city",
            "zip": "1234",
            "phone": "+0123456789",
            "country_id": "United States",
            "state_id": "California (US)",
        };
        for (const [fieldName, expectedValue] of Object.entries(expectedValues)) {
            assert.strictEqual(target.querySelector(`[name=${fieldName}] input`).value, expectedValue, `${fieldName} should be filled`);
        }
    });

    QUnit.test("Partner autocomplete : Company type = Company / VAT search", async function (assert) {
        assert.expect(12);

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
            3,
            "Odoo read_by_vat options should be shown"
        );

        // Click on the first option - "First company"
        await click(autocompleteContainer.querySelectorAll('ul li')[0], null);

        // Check that the fields have been filled
        const expectedValues = {
            "website": "firstcompany.com",
            "name": "First company",
            "vat": "Some VAT number",
            "street": "Some street",
            "city": "Some city",
            "zip": "1234",
            "phone": "+0123456789",
            "country_id": "United States",
            "state_id": "California (US)",
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
            8,
            "Clearbit and Odoo autocomplete options should be shown"
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
            6,
            "Clearbit and Odoo autocomplete options should be shown"
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
            "website": "secondcompany.com",
            "name": "Second company",
            "vat": "Some VAT number",
            "street": "Some street",
            "city": "Some city",
            "zip": "1234",
            "phone": "+0123456789",
            "country_id": "United States",
            "state_id": "California (US)",
        };
        for (const [fieldName, expectedValue] of Object.entries(expectedValues)) {
            assert.strictEqual(target.querySelector(`[name=${fieldName}] input`).value, expectedValue, `${fieldName} should be filled`);
        }
    });
});
