odoo.define('web.domain_selector_tests', function (require) {
"use strict";

var DomainSelector = require("web.DomainSelector");
var testUtils = require("web.test_utils");

QUnit.module('widgets', {}, function () {

QUnit.module('DomainSelector', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    foo: {string: "Foo", type: "char", searchable: true},
                    bar: {string: "Bar", type: "boolean", searchable: true},
                    nice_datetime: {string: "Datetime", type: "datetime", searchable: true},
                    product_id: {string: "Product", type: "many2one", relation: "product", searchable: true},
                },
                records: [{
                    id: 1,
                    foo: "yop",
                    bar: true,
                    product_id: 37,
                }, {
                    id: 2,
                    foo: "blip",
                    bar: true,
                    product_id: false,
                }, {
                    id: 4,
                    foo: "abc",
                    bar: false,
                    product_id: 41,
                }],
                onchanges: {},
            },
            product: {
                fields: {
                    name: {string: "Product Name", type: "char", searchable: true}
                },
                records: [{
                    id: 37,
                    display_name: "xphone",
                }, {
                    id: 41,
                    display_name: "xpad",
                }]
            },
        };
    },
}, function () {

    QUnit.test("creating a domain from scratch", async function (assert) {
        assert.expect(13);

        var $target = $("#qunit-fixture");

        // Create the domain selector and its mock environment
        var domainSelector = new DomainSelector(null, "partner", [], {
            readonly: false,
            debugMode: true,
        });
        await testUtils.mock.addMockEnvironment(domainSelector, {data: this.data});
        await domainSelector.appendTo($target);

        // As we gave an empty domain, there should be a visible button to add
        // the first domain part
        var $domainAddFirstNodeButton = domainSelector.$(".o_domain_add_first_node_button:visible");
        assert.strictEqual($domainAddFirstNodeButton.length, 1,
            "there should be a button to create first domain element");

        // Clicking on the button should add a visible field selector in the
        // widget so that the user can change the field chain
        await testUtils.dom.click($domainAddFirstNodeButton);
        var $fieldSelector = domainSelector.$(".o_field_selector:visible");
        assert.strictEqual($fieldSelector.length, 1,
            "there should be a field selector");

        // Focusing the field selector input should open a field selector popover
        $fieldSelector.trigger('focusin');
        await testUtils.nextTick();
        var $fieldSelectorPopover = $fieldSelector.find(".o_field_selector_popover:visible");
        assert.strictEqual($fieldSelectorPopover.length, 1,
            "field selector popover should be visible");

        // The field selector popover should contain the list of "partner"
        // fields. "Bar" should be among them.
        var $lis = $fieldSelectorPopover.find("li");
        var $barLi = $();
        $lis.each(function () {
            var $li = $(this);
            if ($li.html().indexOf("Bar") >= 0) {
                $barLi = $li;
            }
        });
        assert.strictEqual($barLi.length, 1,
            "field selector popover should contain the 'Bar' field");

        // Clicking the "Bar" field should change the internal domain and this
        // should be displayed in the debug input
        await testUtils.dom.click($barLi);
        assert.strictEqual(
            domainSelector.$(".o_domain_debug_input").val(),
            '[["bar","=",True]]',
            "the domain input should contain a domain with 'bar'"
        );

        // There should be a "+" button to add a domain part; clicking on it
        // should add the default "['id', '=', 1]" domain
        var $plus = domainSelector.$(".fa-plus-circle");
        assert.strictEqual($plus.length, 1, "there should be a '+' button");
        await testUtils.dom.click($plus);
        assert.strictEqual(
            domainSelector.$(".o_domain_debug_input").val(),
            '["&",["bar","=",True],["id","=",1]]',
            "the domain input should contain a domain with 'bar' and 'id'");

        // There should be two "..." buttons to add a domain group; clicking on
        // the first one, should add this group with defaults "['id', '=', 1]"
        // domains and the "|" operator
        var $dots = domainSelector.$(".fa-ellipsis-h");
        assert.strictEqual($dots.length, 2, "there should be two '...' buttons");
        await testUtils.dom.click($dots.first());
        assert.strictEqual(
            domainSelector.$(".o_domain_debug_input").val(),
            '["&","&",["bar","=",True],"|",["id","=",1],["id","=",1],["id","=",1]]',
            "the domain input should contain a domain with 'bar', 'id' and a subgroup"
        );

        // Changing the domain input to update the subgroup to use the "foo"
        // field instead of "id" should rerender the widget and adapt the
        // widget suggestions
        domainSelector.$(".o_domain_debug_input").val('["&","&",["bar","=",True],"|",["foo","=","hello"],["id","=",1],["id","=",1]]').change();
        await testUtils.nextTick();
        assert.strictEqual(domainSelector.$(".o_field_selector").eq(1).find("input.o_field_selector_debug").val(), "foo",
            "the second field selector should now contain the 'foo' value");
        assert.ok(domainSelector.$(".o_domain_leaf_operator_select").eq(1).html().indexOf("contains") >= 0,
            "the second operator selector should now contain the 'contains' operator");

        // There should be five "-" buttons to remove domain part; clicking on
        // the two last ones, should leave a domain with only the "bar" and
        // "foo" fields, with the initial "&" operator
        var $minus = domainSelector.$(".o_domain_delete_node_button");
        assert.strictEqual($minus.length, 5, "there should be five 'x' buttons");
        await testUtils.dom.click($minus.last());
        await testUtils.dom.click(domainSelector.$(".o_domain_delete_node_button").last());
        assert.strictEqual(
            domainSelector.$(".o_domain_debug_input").val(),
            '["&",["bar","=",True],["foo","=","hello"]]',
            "the domain input should contain a domain with 'bar' and 'foo'"
        );
        domainSelector.destroy();
    });

    QUnit.test("building a domain with a datetime", async function (assert) {
        assert.expect(2);

        var $target = $("#qunit-fixture");

        // Create the domain selector and its mock environment
        var domainSelector = new DomainSelector(null, "partner", [["nice_datetime", "=", "2017-03-27 15:42:00"]], {
            readonly: false,
        });
        await testUtils.mock.addMockEnvironment(domainSelector, {data: this.data});
        await domainSelector.appendTo($target);

        // Check that there is a datepicker to choose the date
        var $datepicker = domainSelector.$(".o_datepicker:visible");
        assert.strictEqual($datepicker.length, 1,
            "there should be a datepicker");

        var val = $datepicker.find('input').val();
        await testUtils.dom.openDatepicker($datepicker);
        await testUtils.dom.clickFirst($('.bootstrap-datetimepicker-widget :not(.today)[data-action="selectDay"]'));
        assert.notEqual(domainSelector.$(".o_datepicker:visible input").val(), val,
            "datepicker value should have changed");
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget a[data-action=close]'));

        domainSelector.destroy();
    });

    QUnit.test("building a domain with a m2o without following the relation", async function (assert) {
        assert.expect(1);

        var $target = $("#qunit-fixture");

        // Create the domain selector and its mock environment
        var domainSelector = new DomainSelector(null, "partner", [["product_id", "ilike", 1]], {
            debugMode: true,
            readonly: false,
        });
        await testUtils.mock.addMockEnvironment(domainSelector, {data: this.data});
        await domainSelector.appendTo($target);

        await testUtils.fields.editAndTrigger(domainSelector.$('.o_domain_leaf_value_input'),
            'pad', ['input', 'change']);
        assert.strictEqual(domainSelector.$('.o_domain_debug_input').val(), '[["product_id","ilike","pad"]]',
            "string should have been allowed as m2o value");

        domainSelector.destroy();
    });

    QUnit.test("editing a domain with `parent` key", async function (assert) {
        assert.expect(1);

        var $target = $("#qunit-fixture");

        // Create the domain selector and its mock environment
        var domainSelector = new DomainSelector(null, "product", "[['name','=',parent.foo]]", {
            debugMode: true,
            readonly: false,
        });
        await testUtils.mock.addMockEnvironment(domainSelector, {data: this.data});
        await domainSelector.appendTo($target);

        assert.strictEqual(domainSelector.$el.text(), "This domain is not supported.",
            "an error message should be displayed because of the `parent` key");

        domainSelector.destroy();
    });

    QUnit.test("creating a domain with a default option", async function (assert) {
        assert.expect(1);

        var $target = $("#qunit-fixture");

        // Create the domain selector and its mock environment
        var domainSelector = new DomainSelector(null, "partner", [], {
            readonly: false,
            debugMode: true,
            default: [["foo","=","kikou"]],
        });
        await testUtils.mock.addMockEnvironment(domainSelector, {data: this.data});
        await domainSelector.appendTo($target);

        // Clicking on the button should add a visible field selector in the
        // widget so that the user can change the field chain
        await testUtils.dom.click(domainSelector.$(".o_domain_add_first_node_button:visible"));

        assert.strictEqual(
            domainSelector.$(".o_domain_debug_input").val(),
            '[["foo","=","kikou"]]',
            "the domain input should contain the default domain");

        domainSelector.destroy();
    });
});
});
});
