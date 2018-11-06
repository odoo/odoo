odoo.define('partner_autocomplete.tests', function (require) {
    "use strict";

    var FormView = require('web.FormView');
    var concurrency = require('web.concurrency');
    var testUtils = require("web.test_utils");
    var AutocompleteCore = require('partner.autocomplete.core');
    var AutocompleteField = require('partner.autocomplete.fieldchar');
    var PartnerField = require('partner.autocomplete.many2one');

    var createView = testUtils.createAsyncView;

    function _compareResultFields(assert, form, fields, createData) {
        var type, formatted, $fieldInput;

        _.each(createData, function (val, key) {
            if (fields[key]) {
                if (key === 'image') {
                    if (val) val = 'data:image/png;base64,' + val;
                    assert.strictEqual(form.$(".o_field_image img").attr("data-src"), val, 'image value should have been updated to "' + val + '"');
                } else {
                    type = fields[key].type;
                    $fieldInput = form.$('input[name="' + key + '"]');
                    if ($fieldInput.length) {
                        formatted = $fieldInput.val();
                        formatted = type === 'integer' ? parseInt(formatted, 10) : formatted;
                        assert.strictEqual(
                            formatted,
                            val === false ? 0 : val,
                            key + ' value should have been updated to "' + val + '"'
                        );
                    }

                }
            }
        });
    }

    QUnit.module('partner_autocomplete', {
        before: function () {
            var suggestions = [
                {name: "Odoo", website: "odoo.com", domain: "odoo.com", logo: "odoo.com/logo.png", vat: "BE0477472701"}
            ];

            var enrich_data = {
                country_id: 20,
                state_id: false,
                partner_gid: 1,
                website: "odoo.com",
                comment: "Comment on Odoo",
                street: "40 Chaussée de Namur",
                city: "Ramillies",
                zip: "1367",
                phone: "+1 650-691-3277",
                email: "info@odoo.com",
                vat: "BE0477472701",
            };

            testUtils.patch(AutocompleteCore, {
                _getBase64Image: function (url) {
                    return $.when(url === "odoo.com/logo.png" ? "odoobase64" : "");
                },
                isOnline: function () {
                    return true;
                },
                getCreateData: function (company) {
                    var self = this;
                    var def = this._super.apply(this, arguments);
                    def.then(function (data) {
                        self._createData = data.company;
                    });
                    return def;
                },
                enrichCompany: function (company) {
                    return $.when(enrich_data);
                },
                _getOdooSuggestions(value, isVAT) {
                    var results = _.filter(suggestions, function (suggestion) {
                        value = value ? value.toLowerCase() : '';
                        if (isVAT) return (suggestion.vat.toLowerCase().indexOf(value) >= 0);
                        else return (suggestion.name.toLowerCase().indexOf(value) >= 0);
                    });
                    return $.when(results);
                },
                _getClearbitSuggestions(value) {
                    return this._getOdooSuggestions(value);
                },
            });

            testUtils.patch(AutocompleteField, {
                debounceSuggestions: 0,
            });
        },
        beforeEach: function () {
            this.data = {
                'res.partner': {
                    fields: {
                        company_type: {
                            string: "Company Type",
                            type: "selection",
                            selection: [["company", "Company"], ["individual", "Individual"]],
                            searchable: true
                        },
                        name: {string: "Name", type: "char", searchable: true},
                        parent_id: {string: "Company", type: "many2one", relation: "res.partner"},
                        website: {string: "Website", type: "char", searchable: true},
                        image: {string: "Image", type: "binary", searchable: true},
                        email: {string: "Email", type: "char", searchable: true},
                        phone: {string: "Phone", type: "char", searchable: true},
                        street: {string: "Street", type: "char", searchable: true},
                        city: {string: "City", type: "char", searchable: true},
                        zip: {string: "Zip", type: "char", searchable: true},
                        state_id: {string: "State", type: "integer", searchable: true},
                        country_id: {string: "Country", type: "integer", searchable: true},
                        comment: {string: "Comment", type: "char", searchable: true},
                        vat: {string: "Vat", type: "char", searchable: true},
                        is_company: {string: "Is comapny", type: "bool", searchable: true},
                        partner_gid: {string: "Company data ID", type: "integer", searchable: true},
                    },
                    records: [],
                    onchanges: {
                        company_type: function (obj) {
                            obj.is_company = obj.company_type === 'company';
                        },
                    },
                },
            };
        },
        after: function () {
            testUtils.unpatch(AutocompleteField);
            testUtils.unpatch(AutocompleteCore);
        },
    });

    QUnit.test("Partner autocomplete : Company type = Individual", function (assert) {
        assert.expect(2);
        var done = assert.async();
        createView({
            View: FormView,
            model: 'res.partner',
            data: this.data,
            arch:
                '<form>' +
                '<field name="company_type"/>' +
                '<field name="name" widget="field_partner_autocomplete"/>' +
                '<field name="website"/>' +
                '<field name="image" widget="image"/>' +
                '</form>',
        }).then(function (form){
            // Set company type to Individual
            var $company_type = form.$("select[name='company_type']");
            $company_type.val('"individual"').trigger('change');

            // Check input exists
            var $input = form.$(".o_field_partner_autocomplete > input:visible");
            assert.strictEqual($input.length, 1, "there should be an <input/> for the Partner field");

            // Change input val and assert nothing happens
            $input.val("odoo").trigger("input");
            var $dropdown = form.$(".o_field_partner_autocomplete .dropdown-menu:visible");
            assert.strictEqual($dropdown.length, 0, "there should not be an opened dropdown");

            form.destroy();

            done();
        });
    });


    QUnit.test("Partner autocomplete : Company type = Company / Name search", function (assert) {
        assert.expect(21);
        var done = assert.async();
        var fields = this.data['res.partner'].fields;
        createView({
            View: FormView,
            model: 'res.partner',
            data: this.data,
            arch:
                '<form>' +
                '<field name="company_type"/>' +
                '<field name="name" widget="field_partner_autocomplete"/>' +
                '<field name="website"/>' +
                '<field name="image" widget="image"/>' +
                '<field name="email"/>' +
                '<field name="phone"/>' +
                '<field name="street"/>' +
                '<field name="city"/>' +
                '<field name="state_id"/>' +
                '<field name="zip"/>' +
                '<field name="country_id"/>' +
                '<field name="comment"/>' +
                '<field name="vat"/>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method) {
                    assert.step(args.method);
                }
                if (route === "/web/static/src/img/placeholder.png"
                    || route === "odoo.com/logo.png"
                    || route === "data:image/png;base64,odoobase64") { // land here as it is not valid base64 content
                    return $.when();
                }
                return this._super.apply(this, arguments);
            },
        }).then(function (form){
            // Set company type to Company
            var $company_type = form.$("select[name='company_type']");
            $company_type.val('"company"').trigger('change');

            // Check input exists
            var $input = form.$(".o_field_partner_autocomplete > input:visible");
            assert.strictEqual($input.length, 1, "there should be an <input/> for the field");

            // Change input val and assert changes
            $input.val("odoo").trigger("input");

            var $dropdown = form.$(".o_field_partner_autocomplete .dropdown-menu:visible");
            assert.strictEqual($dropdown.length, 1, "there should be an opened dropdown");
            assert.strictEqual($dropdown.children().length, 1, "there should be only one proposition");

            $dropdown.find("a").first().click();
            $input = form.$(".o_field_partner_autocomplete > input");
            assert.strictEqual($input.val(), "Odoo", "Input value should have been updated to \"Odoo\"");
            assert.strictEqual(form.$("input.o_field_widget").val(), "odoo.com", "website value should have been updated to \"odoo.com\"");

            _compareResultFields(assert, form, fields, AutocompleteCore._createData);

            // Try suggestion with bullshit query
            $input.val("ZZZZZZZZZZZZZZZZZZZZZZ").trigger("input");
            $dropdown = form.$(".o_field_partner_autocomplete .dropdown-menu:visible");
            assert.strictEqual($dropdown.length, 0, "there should be no opened dropdown when no result");

            // Try autocomplete again
            $input.val("odoo").trigger("input");
            $dropdown = form.$(".o_field_partner_autocomplete .dropdown-menu:visible");
            assert.strictEqual($dropdown.length, 1, "there should be an opened dropdown when typing odoo letters again");

            // Test if dropdown closes on focusout
            $input.trigger("focusout");
            $dropdown = form.$(".o_field_partner_autocomplete .dropdown-menu:visible");
            assert.strictEqual($dropdown.length, 0, "unfocusing the input should close the dropdown");

            form.destroy();

            done();
        });
    });

    QUnit.test("Partner autocomplete : Company type = Company / VAT search", function (assert) {
        assert.expect(32);
        var done = assert.async();
        var fields = this.data['res.partner'].fields;
        createView({
            View: FormView,
            model: 'res.partner',
            data: this.data,
            arch:
                '<form>' +
                '<field name="company_type"/>' +
                '<field name="name" widget="field_partner_autocomplete"/>' +
                '<field name="website"/>' +
                '<field name="image" widget="image"/>' +
                '<field name="email"/>' +
                '<field name="phone"/>' +
                '<field name="street"/>' +
                '<field name="city"/>' +
                '<field name="state_id"/>' +
                '<field name="zip"/>' +
                '<field name="country_id"/>' +
                '<field name="comment"/>' +
                '<field name="vat"/>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method) {
                    assert.step(args.method);
                }
                if (route === "/web/static/src/img/placeholder.png"
                    || route === "odoo.com/logo.png"
                    || route === "data:image/png;base64,odoobase64") { // land here as it is not valid base64 content
                    return $.when();
                }
                return this._super.apply(this, arguments);
            },
        }).then(function (form){
            // Set company type to Company
            var $company_type = form.$("select[name='company_type']");
            $company_type.val('"company"').trigger('change');


            // Check input exists
            var $input = form.$(".o_field_partner_autocomplete > input:visible");
            assert.strictEqual($input.length, 1, "there should be an <input/> for the field");

            // Set incomplete VAT and assert changes
            $input.val("BE047747270").trigger("input");

            var $dropdown = form.$(".o_field_partner_autocomplete .dropdown-menu:visible");
            assert.strictEqual($dropdown.length, 0, "there should be no opened dropdown no results with incomplete VAT number");

            // Set complete VAT and assert changes
            // First suggestion (only vat result)
            $input.val("BE0477472701").trigger("input");
            $dropdown = form.$(".o_field_partner_autocomplete .dropdown-menu:visible");
            assert.strictEqual($dropdown.length, 1, "there should be an opened dropdown");
            assert.strictEqual($dropdown.children().length, 1, "there should be one proposition for complete VAT number");

            $dropdown.find("a").first().click();

            $input = form.$(".o_field_partner_autocomplete > input");
            assert.strictEqual($input.val(), "Odoo", "Input value should have been updated to \"Odoo\"");

            _compareResultFields(assert, form, fields, AutocompleteCore._createData);

            // Set complete VAT and assert changes
            // Second suggestion (only vat + clearbit result)
            $input.val("BE0477472701").trigger("input");
            $dropdown = form.$(".o_field_partner_autocomplete .dropdown-menu:visible");
            assert.strictEqual($dropdown.length, 1, "there should be an opened dropdown");
            assert.strictEqual($dropdown.children().length, 1, "there should be one proposition for complete VAT number");

            $dropdown.find("a").first().click();

            $input = form.$(".o_field_partner_autocomplete > input");
            assert.strictEqual($input.val(), "Odoo", "Input value should have been updated to \"Odoo\"");

            _compareResultFields(assert, form, fields, AutocompleteCore._createData);

            // Test if dropdown closes on focusout
            $input.trigger("focusout");
            $dropdown = form.$(".o_field_partner_autocomplete .dropdown-menu:visible");
            assert.strictEqual($dropdown.length, 0, "unfocusing the input should close the dropdown");

            form.destroy();

            done();
        });
    });

    QUnit.test("Partner autocomplete : render Many2one", function (assert) {
        var done = assert.async();
        assert.expect(3);

        var M2O_DELAY = PartnerField.prototype.AUTOCOMPLETE_DELAY;
        PartnerField.prototype.AUTOCOMPLETE_DELAY = 0;

        createView({
            View: FormView,
            model: 'res.partner',
            data: this.data,
            arch:
                '<form>' +
                    '<field name="name"/>' +
                    '<field name="parent_id" widget="res_partner_many2one"/>' +
                '</form>',
        }).then(function (form) {
            var $input = form.$('.o_field_many2one[name="parent_id"] input:visible');
            assert.strictEqual($input.length, 1, "there should be an <input/> for the Many2one");

            $input.val('odoo').trigger('input');

            concurrency.delay(0).then(function () {
                var $dropdown = $input.autocomplete('widget');
                assert.strictEqual($dropdown.length, 1, "there should be an opened dropdown");
                assert.ok($dropdown.is('.o_partner_autocomplete_dropdown'), 
                    "there should be a partner_autocomplete");

                PartnerField.prototype.AUTOCOMPLETE_DELAY = M2O_DELAY;
                form.destroy();

                done();
            });
        });
    });
});
