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
        assert.expect(14);

        var $target = $("#qunit-fixture");

        // Create the field selector and its mock environment
        var fieldSelector = new ModelFieldSelector(null, "partner", [], {
            readonly: false,
            debugMode: true,
        });
        testUtils.addMockEnvironment(fieldSelector, {data: this.data});
        fieldSelector.appendTo($target);
        var $value = fieldSelector.$("> .o_field_selector_value");

        // Focusing the field selector input should open a field selector popover
        fieldSelector.$el.trigger('focusin');
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
        assert.strictEqual(getValueFromDOM($value), "Bar",
            "field selector value should be displayed with a 'Bar' tag");

        assert.deepEqual(fieldSelector.getSelectedField(), {
            model: "partner",
            name: "bar",
            searchable: true,
            string: "Bar",
            type: "boolean",
        }, "the selected field should be correctly set");

        // Focusing the input again should open the same popover
        fieldSelector.$el.trigger('focusin');
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
        assert.strictEqual(getValueFromDOM($value), "Product -> Product Name",
            "field selector value should be displayed with two tags: 'Product' and 'Product Name'");

        // Remove the current selection and recreate it again
        fieldSelector.$el.trigger('focusin');
        fieldSelector.$('.o_field_selector_prev_page').click();
        fieldSelector.$('.o_field_selector_close').click();

        fieldSelector.$el.trigger('focusin');
        $fieldSelectorPopover = fieldSelector.$(".o_field_selector_popover:visible");
        $lis = $fieldSelectorPopover.find("li");
        $productLi = $();
        $lis.each(function () {
            var $li = $(this);
            if ($li.html().indexOf("Product") >= 0) {
                $productLi = $li;
            }
        });
        assert.strictEqual($productLi.length, 1,
            "field selector popover should contain the 'Product' field");

        $productLi.click();
        $lis = $fieldSelectorPopover.find("li");
        $lis.first().click();
        assert.notOk($fieldSelectorPopover.is("visible"),
            "field selector popover should be closed now");
        assert.strictEqual(getValueFromDOM($value), "Product -> Product Name",
            "field selector value should be displayed with two tags: 'Product' and 'Product Name'");

        fieldSelector.destroy();

        function getValueFromDOM($dom) {
            return _.map($dom.find(".o_field_selector_chain_part"), function (part) {
                return $(part).text().trim();
            }).join(" -> ");
        }
    });

    QUnit.test("use the filter option", function (assert) {
        assert.expect(2);

        var $target = $("#qunit-fixture");

        // Create the field selector and its mock environment
        var fieldSelector = new ModelFieldSelector(null, "partner", [], {
            readonly: false,
            filter: function (field) {
                return field.type === 'many2one';
            },
        });
        testUtils.addMockEnvironment(fieldSelector, {data: this.data});
        fieldSelector.appendTo($target);

        fieldSelector.$el.trigger('focusin');
        var $fieldSelectorPopover = fieldSelector.$(".o_field_selector_popover:visible");
        var $lis = $fieldSelectorPopover.find("li");
        assert.strictEqual($lis.length, 1, "there should only be one element");
        assert.strictEqual($lis.text().trim(), "Product", "the available field should be the many2one");

        fieldSelector.destroy();
    });

    QUnit.test("default `showSearchInput` option", function (assert) {
        assert.expect(6);

        var $target = $("#qunit-fixture");

        // Create the field selector and its mock environment
        var fieldSelector = new ModelFieldSelector(null, "partner", [], {
            readonly: false,
        });
        testUtils.addMockEnvironment(fieldSelector, {data: this.data});
        fieldSelector.appendTo($target);

        fieldSelector.$el.trigger('focusin');
        var $fieldSelectorPopover = fieldSelector.$(".o_field_selector_popover:visible");
        var $searchInput = $fieldSelectorPopover.find(".o_field_selector_search input");
        assert.strictEqual($searchInput.length, 1, "there should be a search input");

        // without search
        assert.strictEqual($fieldSelectorPopover.find("li").length, 3, "there should be three available fields");
        assert.strictEqual($fieldSelectorPopover.find("li").text().trim().replace(/\s+/g, ' '), "Bar Foo Product", "the available field should be correct");
        $searchInput.val('xx').trigger('keyup');

        assert.strictEqual($fieldSelectorPopover.find("li").length, 0, "there shouldn't be any element");
        $searchInput.val('Pro').trigger('keyup');
        assert.strictEqual($fieldSelectorPopover.find("li").length, 1, "there should only be one element");
        assert.strictEqual($fieldSelectorPopover.find("li").text().trim().replace(/\s+/g, ' '), "Product", "the available field should be the Product");

        fieldSelector.destroy();
    });

    QUnit.test("false `showSearchInput` option", function (assert) {
        assert.expect(1);

        var $target = $("#qunit-fixture");

        // Create the field selector and its mock environment
        var fieldSelector = new ModelFieldSelector(null, "partner", [], {
            readonly: false,
            showSearchInput: false,
        });
        testUtils.mock.addMockEnvironment(fieldSelector, { data: this.data });
        fieldSelector.appendTo($target);

        fieldSelector.$el.trigger('focusin');
        var $fieldSelectorPopover = fieldSelector.$(".o_field_selector_popover:visible");
        var $searchInput = $fieldSelectorPopover.find(".o_field_selector_search input");
        assert.strictEqual($searchInput.length, 0, "there should be no search input");

        fieldSelector.destroy();
    });
});
});
});
