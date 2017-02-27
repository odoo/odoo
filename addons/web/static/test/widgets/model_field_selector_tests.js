odoo.define('web.model_field_selector_tests', function (require) {
"use strict";

var ModelFieldSelector = require("web.ModelFieldSelector");
var testUtils = require("web.test_utils");

QUnit.module('widgets', {}, function () {

QUnit.module('ModelFieldSelector', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    foo: {string: "Foo", type: "char", searchable: true},
                    bar: {string: "Bar", type: "boolean", searchable: true},
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

    QUnit.test("creating a field chain from scratch", function (assert) {
        assert.expect(10);

        var $target = $("#qunit-fixture");

        // Create the field selector and its mock environment
        var fieldSelector = new ModelFieldSelector(null, "partner", "", {
            debugMode: true,
        });
        testUtils.addMockEnvironment(fieldSelector, {data: this.data});
        fieldSelector.appendTo($target);

        // Focusing the field selector input should open a field selector popover
        var $input = fieldSelector.$("> input");
        $input.trigger('focusin');
        var $fieldSelectorPopover = fieldSelector.$(".o_field_selector_popover:visible");
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

        // Clicking the "Bar" field should close the popover and set the field
        // chain to "bar" as it is a basic field
        $barLi.click();
        assert.notOk($fieldSelectorPopover.is("visible"),
            "field selector popover should be closed now");
        assert.strictEqual($input.val(), "bar",
            "field selector input value should be 'bar'");

        // Focusing the input again should open the same popover
        $input.trigger('focusin');
        assert.ok($fieldSelectorPopover.is(":visible"),
            "field selector popover should be visible");

        // The field selector popover should contain the list of "partner"
        // fields. "Product" should be among them.
        $lis = $fieldSelectorPopover.find("li");
        var $productLi = $();
        $lis.each(function () {
            var $li = $(this);
            if ($li.html().indexOf("Product") >= 0) {
                $productLi = $li;
            }
        });
        assert.strictEqual($productLi.length, 1,
            "field selector popover should contain the 'Product' field");

        // Clicking on the "Product" field should update the popover to show
        // the product fields (so only "Product Name" should be there)
        $productLi.click();
        $lis = $fieldSelectorPopover.find("li");
        assert.strictEqual($lis.length, 1,
            "there should be only one field proposition for 'product' model");
        assert.ok($lis.first().html().indexOf("Product Name") >= 0,
            "the name of the only suggestion should be 'Product Name'");

        // Clicking on "Product Name" should close the popover and set the chain
        // to "product_id.name"
        $lis.first().click();
        assert.notOk($fieldSelectorPopover.is("visible"),
            "field selector popover should be closed now");
        assert.strictEqual($input.val(), "product_id.name",
            "field selector input value should be 'product_id.name'");
        fieldSelector.destroy();
    });
});
});
});
