/** @odoo-module */

import { createDebugContext } from "@web/core/debug/debug_context";
import { dialogService } from "@web/core/dialog/dialog_service";
import { notificationService } from "@web/core/notifications/notification_service";
import { ormService } from "@web/core/orm_service";
import { registry } from "@web/core/registry";
import { View } from "@web/legacy/owl_view";
import { viewService } from "@web/views/view_service";
import { actionService } from "@web/webclient/actions/action_service";
import { ComponentWrapper } from "web.OwlCompatibility";
import Widget from "web.Widget";
import { makeTestEnv } from "../helpers/mock_env";
import { fakeTitleService } from "../helpers/mock_services";
import { getFixture, nextTick } from "../helpers/utils";
import { addLegacyMockEnvironment } from "../webclient/helpers";

const { Component, hooks, mount, tags } = owl;
const serviceRegistry = registry.category("services");

let target;
let serverData;

const prepareEnv = async () => {
    const baseEnv = await makeTestEnv({ serverData });
    const env = { ...baseEnv, ...createDebugContext(baseEnv) }
    addLegacyMockEnvironment(env, { withLegacyMockServer: true, models: serverData.models });

    odoo.__WOWL_DEBUG__ = {
        root: { env },
    };

    return env;
};

QUnit.module("Owl view", ({ beforeEach }) => {
    beforeEach(async () => {
        serviceRegistry
            .add("action", actionService)
            .add("notification", notificationService)
            .add("view", viewService)
            .add("title", fakeTitleService)
            .add("dialog", dialogService)
            .add("orm", ormService);

        target = getFixture();
        serverData = {
            models: {
                "take.five": {
                    fields: {
                        foo: { type: "char", string: "Foo", searchable: true },
                    },
                    records: [
                        { id: 1, foo: "frodo" },
                        { id: 2, foo: "sam" },
                        { id: 3, foo: "merry" },
                        { id: 4, foo: "pippin" },
                    ],
                },
            },
            views: {
                "take.five,false,list": /* xml */`
                    <list>
                        <field name="foo" />
                    </list>
                `,
                "take.five,false,form": /* xml */`
                    <form>
                        <field name="foo" />
                    </form>
                `,
                "take.five,false,search": /* xml */`
                    <search>
                        <field name="foo" />
                    </search>
                `,
            },
        }
    });

    QUnit.test("Instantiate multiple view components", async (assert) => {
        assert.expect(8);

        let parentState;
        class Parent extends Component {
            setup() {
                this.state = hooks.useState({
                    resModel: "take.five",
                    resId: 1,
                    domain: [],
                });
                parentState = this.state;
            }
        }

        Parent.components = { View };
        Parent.template = tags.xml/* xml */ `
            <div class="parent">
                <View type="'list'" resModel="state.resModel" domain="state.domain" views="[[false, 'search']]" />
                <View type="'form'" resModel="state.resModel" resId="state.resId" withControlPanel="false" />
            </div>
        `;

        const env = await prepareEnv();
        await mount(Parent, { env, target });

        assert.containsN(target, ".o_view_controller", 2);
        assert.containsOnce(target, ".o_control_panel");
        assert.containsOnce(target, ".o_list_view");
        assert.containsOnce(target, ".o_form_view");

        // Change domain
        assert.containsN(target, ".o_data_row", 4);

        parentState.domain.push(["id", ">", 2]);
        await nextTick();

        assert.containsN(target, ".o_data_row", 2);

        // Change res id
        assert.strictEqual($(".o_form_view .o_field_char[name=foo]").text(), "frodo");

        parentState.resId = 2;
        await nextTick()

        assert.strictEqual($(".o_form_view .o_field_char[name=foo]").text(), "sam");
    });

    QUnit.test("Works inside of a component wrapper", async (assert) => {
        assert.expect(1);

        const legacyParent = new Widget();
        const wrapper = new ComponentWrapper(legacyParent, View, { type: "list", resModel: "take.five" });

        await prepareEnv();

        await legacyParent.appendTo(target);
        await wrapper.mount(legacyParent.el);

        assert.containsN(legacyParent.el, ".o_data_row", 4);
    });
});
