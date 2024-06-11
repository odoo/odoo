/** @odoo-module **/

import { Component, xml } from "@odoo/owl";
import { DomainSelectorDialog } from "@web/core/domain_selector_dialog/domain_selector_dialog";
import { click, dragAndDrop, getFixture, mount } from "../helpers/utils";
import { makeDialogTestEnv } from "../helpers/mock_env";
import { registry } from "@web/core/registry";
import { notificationService } from "@web/core/notifications/notification_service";
import { ormService } from "@web/core/orm_service";
import { uiService } from "@web/core/ui/ui_service";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { makeFakeLocalizationService } from "../helpers/mock_services";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { fieldService } from "@web/core/field_service";
import { popoverService } from "@web/core/popover/popover_service";
import { nameService } from "@web/core/name_service";

/**
 * @typedef {Record<keyof DomainSelectorDialog.props, any>} Props
 */

/**
 * @param {Partial<Props> & { mockRPC: Function }} [params]
 */
async function makeDomainSelectorDialog(params = {}) {
    const props = { ...params };
    const mockRPC = props.mockRPC;
    delete props.mockRPC;

    class Parent extends Component {
        static components = { DomainSelectorDialog };
        static template = xml`<DomainSelectorDialog t-props="domainSelectorProps"/>`;
        setup() {
            this.domainSelectorProps = {
                resModel: "partner",
                readonly: false,
                domain: "[]",
                close: () => {},
                onConfirm: () => {},
                ...props,
            };
        }
    }

    const env = await makeDialogTestEnv({ serverData, mockRPC });
    await mount(MainComponentsContainer, fixture, { env });
    return mount(Parent, fixture, { env, props });
}

/** @type {Element} */
let fixture;
let serverData;

QUnit.module("Components", (hooks) => {
    hooks.beforeEach(async () => {
        serverData = {
            models: {
                partner: {
                    fields: {
                        foo: { string: "Foo", type: "char", searchable: true },
                        bar: { string: "Bar", type: "boolean", searchable: true },
                        product_id: {
                            string: "Product",
                            type: "many2one",
                            relation: "product",
                            searchable: true,
                        },
                        datetime: { string: "Date Time", type: "datetime", searchable: true },
                        int: { string: "Integer", type: "integer", searchable: true },
                        json_field: { string: "Json Field", type: "json", searchable: true },
                    },
                    records: [
                        { id: 1, foo: "yop", bar: true, product_id: 37 },
                        { id: 2, foo: "blip", bar: true, product_id: false },
                        { id: 4, foo: "abc", bar: false, product_id: 41 },
                    ],
                    onchanges: {},
                },
                product: {
                    fields: {
                        name: { string: "Product Name", type: "char", searchable: true },
                    },
                    records: [
                        { id: 37, display_name: "xphone" },
                        { id: 41, display_name: "xpad" },
                    ],
                },
            },
        };

        registry.category("services").add("notification", notificationService);
        registry.category("services").add("orm", ormService);
        registry.category("services").add("ui", uiService);
        registry.category("services").add("hotkey", hotkeyService);
        registry.category("services").add("localization", makeFakeLocalizationService());
        registry.category("services").add("popover", popoverService);
        registry.category("services").add("field", fieldService);
        registry.category("services").add("name", nameService);

        fixture = getFixture();
    });

    QUnit.module("DomainSelectorDialog");

    QUnit.test("a domain with a user context dynamic part is valid", async (assert) => {
        await makeDomainSelectorDialog({
            domain: "[('foo', '=', uid)]",
            onConfirm(domain) {
                assert.strictEqual(domain, "[('foo', '=', uid)]");
                assert.step("confirmed");
            },
            mockRPC(route) {
                if (route === "/web/domain/validate") {
                    assert.step("validation");
                    return true;
                }
            },
        });
        const confirmButton = fixture.querySelector(".o_dialog footer button");
        await click(confirmButton);
        assert.verifySteps(["validation", "confirmed"]);
    });

    QUnit.test("can extend eval context", async (assert) => {
        await makeDomainSelectorDialog({
            domain: "['&', ('foo', '=', uid), ('bar', '=', var)]",
            context: { uid: 99, var: "true" },
            onConfirm(domain) {
                assert.strictEqual(domain, "['&', ('foo', '=', uid), ('bar', '=', var)]");
                assert.step("confirmed");
            },

            mockRPC(route) {
                if (route === "/web/domain/validate") {
                    assert.step("validation");
                    return true;
                }
            },
        });
        const confirmButton = fixture.querySelector(".o_dialog footer button");
        await click(confirmButton);
        assert.verifySteps(["validation", "confirmed"]);
    });

    QUnit.test("a domain with an unknown expression is not valid", async (assert) => {
        await makeDomainSelectorDialog({
            domain: "[('foo', '=', unknown)]",
            onConfirm() {
                assert.step("confirmed");
            },
            mockRPC(route) {
                if (route === "/web/domain/validate") {
                    assert.step("validation");
                }
            },
        });
        const confirmButton = fixture.querySelector(".o_dialog footer button");
        await click(confirmButton);
        assert.verifySteps([]);
    });

    QUnit.test("model_field_selector should close on dialog drag", async (assert) => {
        await makeDomainSelectorDialog({
            domain: "[('foo', '=', unknown)]",
        });

        assert.containsNone(fixture, ".o_model_field_selector_popover");
        await click(fixture, ".o_model_field_selector_value");
        assert.containsOnce(fixture, ".o_model_field_selector_popover");

        const header = fixture.querySelector(".modal-header");
        const headerRect = header.getBoundingClientRect();
        await dragAndDrop(header, document.body, {
            // the util function sets the source coordinates at (x; y) + (w/2; h/2)
            // so we need to move the dialog based on these coordinates.
            x: headerRect.x + headerRect.width / 2 + 20,
            y: headerRect.y + headerRect.height / 2 + 50,
        });
        assert.containsNone(fixture, ".o_model_field_selector_popover");
    });
});
