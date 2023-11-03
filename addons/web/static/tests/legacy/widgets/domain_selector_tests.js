/** @odoo-module **/

import { click, getFixture } from "@web/../tests/helpers/utils";
import DomainSelector from "web.DomainSelector";
import testUtilsMock from "web.test_utils_mock";

let serverData;

QUnit.module("Widgets", {}, function () {
    QUnit.module("DomainSelector", {
        beforeEach() {
            serverData = {
                partner: {
                    fields: {
                        foo: { string: "Foo", type: "char", searchable: true },
                        bar: { string: "Bar", type: "boolean", searchable: true },
                        nice_datetime: { string: "Datetime", type: "datetime", searchable: true },
                        product_id: {
                            string: "Product",
                            type: "many2one",
                            relation: "product",
                            searchable: true,
                        },
                    },
                    records: [
                        {
                            id: 1,
                            foo: "yop",
                            bar: true,
                            product_id: 37,
                        },
                        {
                            id: 2,
                            foo: "blip",
                            bar: true,
                            product_id: false,
                        },
                        {
                            id: 4,
                            foo: "abc",
                            bar: false,
                            product_id: 41,
                        },
                    ],
                    onchanges: {},
                },
                product: {
                    fields: {
                        name: { string: "Product Name", type: "char", searchable: true },
                    },
                    records: [
                        {
                            id: 37,
                            display_name: "xphone",
                        },
                        {
                            id: 41,
                            display_name: "xpad",
                        },
                    ],
                },
            };
        },
    });

    QUnit.test("deleting domain node", async (assert) => {
        const target = getFixture();
        const domainSelector = new DomainSelector(null, "partner", [], {
            readonly: false,
            debugMode: true,
        });
        await testUtilsMock.addMockEnvironment(domainSelector, {
            debug: QUnit.config.debug,
            data: serverData,
        });
        await domainSelector.appendTo(target);
        await click(target, ".o_domain_add_first_node_button");
        assert.strictEqual(target.querySelector(".o_domain_debug_input").value, '[["id","=",1]]');
        await click(target, ".o_domain_delete_node_button");
        assert.strictEqual(target.querySelector(".o_domain_debug_input").value, "[]");
        domainSelector.destroy();
    });

    QUnit.test("operators option filter available operators", async (assert) => {
        const target = getFixture();
        const domainSelector = new DomainSelector(null, "partner", [], {
            readonly: false,
            debugMode: true,
            operators: ["=", "set"],
        });
        await testUtilsMock.addMockEnvironment(domainSelector, {
            data: serverData,
        });
        await domainSelector.appendTo(target);
        await click(target, ".o_domain_add_first_node_button");
        await click(target, ".o_field_selector_value");
        await click(target, ".o_field_selector_item[data-name=bar]");
        const operators = Array.from(target.querySelectorAll(".o_domain_leaf_operator_select option"))
            .map(element => element.getAttribute("value"));
        assert.deepEqual(operators, ["="]);
        domainSelector.destroy();
    });
});
