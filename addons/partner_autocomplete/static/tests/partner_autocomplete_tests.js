odoo.define('partner_autocomplete.tests', function (require) {
    "use strict";

    var FormView = require('web.FormView');
    var testUtils = require("web.test_utils");
    var FieldAutocomplete = require('partner.autocomplete.fieldchar');

    var createView = testUtils.createView;

    QUnit.module('partner_autocomplete', {
        before: function () {
            this.__field_clearbit_debounce = FieldAutocomplete.prototype.debounceSuggestions;
            FieldAutocomplete.prototype.debounceSuggestions = 0;

            // TODO mock these instead of overriding them

            this.__field_clearbit_getBase64Image = FieldAutocomplete.prototype._getBase64Image;
            FieldAutocomplete.prototype._getBase64Image = function (url) {
                return $.when(url === "odoo.com/logo.png" ? "odoobase64" : "");
            };

            this.__field_clearbit_getClearbitValues = FieldAutocomplete.prototype._getClearbitValues;
            var suggestions = [
                {name: "Odoo", domain: "odoo.com", logo: "odoo.com/logo.png"}
            ];
            FieldAutocomplete.prototype._getClearbitValues = function (value) {
                this.suggestions = _.filter(suggestions, function (suggestion) {
                    return (suggestion.name.toLowerCase().indexOf(value.toLowerCase()) >= 0);
                });
                return $.when();
            };

            this.__field_clearbit_enrichCompany = FieldAutocomplete.prototype._enrichCompany;
            FieldAutocomplete.prototype._enrichCompany = function () {
               return {
                   "country_id": 20,
                   "state_id": false,
                   "website": "odoo.com",
                   "comment": "Comment on Odoo",
                   "street": "40 Chaussée de Namur",
                   "city": "Ramillies",
                   "zip": "1367",
                   "phone": "+1 650-691-3277",
                   "email": "info@odoo.com"
               };
            };
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
                    },
                    records: [],
                    onchanges: {},
                },
            };
        },
        after: function () {
            FieldAutocomplete.prototype.debounceSuggestions = this.__field_clearbit_debounce;
            delete this.__field_clearbit_debounce;

            FieldAutocomplete.prototype._getBase64Image = this.__field_clearbit_getBase64Image;
            delete this.__field_clearbit_getBase64Image;

            FieldAutocomplete.prototype._getClearbitValues = this.__field_clearbit_getClearbitValues;
            delete this.__field_clearbit_getClearbitValues;

            FieldAutocomplete.prototype._enrichCompany = this.__field_clearbit_enrichCompany;
            delete this.__field_clearbit_enrichCompany;
        },
    });

    QUnit.test("Clearbit autocomplete : Company type = Individual", function (assert) {
        assert.expect(2);

        var form = createView({
            View: FormView,
            model: 'res.partner',
            data: this.data,
            arch:
                '<form>' +
                '<field name="company_type"/>' +
                '<field name="name" widget="field_clearbit"/>' +
                '<field name="website"/>' +
                '<field name="image" widget="image"/>' +
                '</form>',
        });

        // Set company type to Individual
        var $company_type = form.$("select[name='company_type']");
        $company_type.val('"individual"').trigger('change');

        // Check input exists
        var $input = form.$(".o_field_clearbit > input:visible");
        assert.strictEqual($input.length, 1, "there should be an <input/> for the clearbit field");

        // Change input val and assert nothing happens
        $input.val("odoo").trigger("input");
        var $dropdown = form.$(".o_field_clearbit .dropdown-menu:visible");
        assert.strictEqual($dropdown.length, 0, "there should not be an opened dropdown");

        form.destroy();
    });


    QUnit.test("Clearbit autocomplete : Company type = Company", function (assert) {
        assert.expect(19);

        var form = createView({
            View: FormView,
            model: 'res.partner',
            data: this.data,
            arch:
                '<form>' +
                '<field name="company_type"/>' +
                '<field name="name" widget="field_clearbit"/>' +
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
        });

        // Set company type to Company
        var $company_type = form.$("select[name='company_type']");
        $company_type.val('"company"').trigger('change');

        // Check input exists
        var $input = form.$(".o_field_clearbit > input:visible");
        assert.strictEqual($input.length, 1, "there should be an <input/> for the clearbit field");

        // Change input val and assert changes
        $input.val("odoo").trigger("input");

        var $dropdown = form.$(".o_field_clearbit .dropdown-menu:visible");
        assert.strictEqual($dropdown.length, 1, "there should be an opened dropdown");
        assert.strictEqual($dropdown.children().length, 1, "there should be only one proposition");

        $dropdown.find("a").first().click();
        $input = form.$(".o_field_clearbit > input");
        assert.strictEqual($input.val(), "Odoo", "name value should have been updated to \"Odoo\"");
        assert.strictEqual(form.$("input.o_field_widget").val(), "odoo.com", "website value should have been updated to \"odoo.com\"");
        assert.strictEqual(form.$(".o_field_image img").attr("data-src"), "data:image/png;base64,odoobase64", "image value should have been updated to \"odoobase64\"");

        var fields = this.data['res.partner'].fields;
        var type, formatted;
        _.each(FieldAutocomplete.prototype._enrichCompany(), function (val, key) {
            if( fields[key] ) {
                type = fields[key].type;
                formatted = form.$('input[name="'+key+'"]').val();
                formatted = type==='integer' ? parseInt(formatted, 10) : formatted;
                assert.strictEqual(
                    formatted,
                    val === false ? 0 : val,
                    key + ' value should have been updated to \"' + val + '"'
                );
            }
        });

        $input.val("ZZZZZZZZZZZZZZZZZZZZZZ").trigger("input");
        $dropdown = form.$(".o_field_clearbit .dropdown-menu:visible");
        assert.strictEqual($dropdown.length, 0, "there should not be an opened dropdown when there is no suggestion");

        $input.val("odoo").trigger("input");
        $dropdown = form.$(".o_field_clearbit .dropdown-menu:visible");
        assert.strictEqual($dropdown.length, 1, "there should be an opened dropdown when typing odoo letters again");

        $input.trigger("focusout");
        $dropdown = form.$(".o_field_clearbit .dropdown-menu:visible");
        assert.strictEqual($dropdown.length, 0, "unfocusing the input should close the dropdown");

        form.destroy();
    });

});