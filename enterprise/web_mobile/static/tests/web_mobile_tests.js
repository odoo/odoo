/** @odoo-module **/

import testUtils from "@web/../tests/legacy_tests/helpers/test_utils";

import { useBackButton } from "@web_mobile/js/core/hooks";
import { accountMethodsForMobile } from "@web_mobile/js/core/mixins";
import mobile from "@web_mobile/js/services/core";
/*import UserPreferencesFormView from "web_mobile.UserPreferencesFormView";*/

import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { patchUserWithCleanup } from "@web/../tests/helpers/mock_services";
import { mount, getFixture, destroy, patchWithCleanup, clickSave, nextTick } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { registry } from "@web/core/registry";

import { Component, useState, xml } from "@odoo/owl";

const MY_IMAGE =
    "iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg==";
const BASE64_SVG_IMAGE =
    "PHN2ZyB4bWxucz0naHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmcnIHdpZHRoPScxNzUnIGhlaWdodD0nMTAwJyBmaWxsPScjMDAwJz48cG9seWdvbiBwb2ludHM9JzAsMCAxMDAsMCA1MCw1MCcvPjwvc3ZnPg==";
const BASE64_PNG_HEADER = "iVBORw0KGg";

let target;
let serverData;

QUnit.module("web_mobile", {
    async beforeEach() {
        target = getFixture();
        serverData = {
            models: {
                partner: {
                    fields: {
                        name: { string: "name", type: "char" },
                        avatar_1920: {},
                        parent_id: { string: "Parent", type: "many2one", relation: "partner" },
                        sibling_ids: {
                            string: "Sibling",
                            type: "many2many",
                            relation: "partner",
                        },
                        phone: {},
                        mobile: {},
                        email: {},
                        street: {},
                        street2: {},
                        city: {},
                        state_id: {},
                        zip: {},
                        country_id: {},
                        website: {},
                        function: {},
                        title: {},
                        date: { string: "A date", type: "date" },
                        datetime: { string: "A datetime", type: "datetime" },
                    },
                    records: [
                        {
                            id: 1,
                            name: "coucou1",
                        },
                        {
                            id: 2,
                            name: "coucou2",
                        },
                        {
                            id: 11,
                            name: "coucou3",
                            avatar_1920: "image",
                            parent_id: 1,
                            phone: "phone",
                            mobile: "mobile",
                            email: "email",
                            street: "street",
                            street2: "street2",
                            city: "city",
                            state_id: "state_id",
                            zip: "zip",
                            country_id: "country_id",
                            website: "website",
                            function: "function",
                            title: "title",
                        },
                    ],
                },
                users: {
                    fields: {
                        name: { string: "name", type: "char" },
                    },
                    records: [],
                },
            },
        };
        setupViewRegistries();
    },
}, function () {
    QUnit.module("useBackButton");

    QUnit.test("component should receive a backbutton event", async function (assert) {
        assert.expect(5);

        patchWithCleanup(mobile.methods, {
            overrideBackButton({ enabled }) {
                assert.step(`overrideBackButton: ${enabled}`);
            },
        });

        class DummyComponent extends Component {
            static template = xml`<div/>`;
            static props = ["*"];
            setup() {
                this._backButtonHandler = useBackButton(this._onBackButton);
            }

            _onBackButton(ev) {
                assert.step(`${ev.type} event`);
            }
        }

        const target = getFixture();
        const env = makeTestEnv();

        const dummy = await mount(DummyComponent, target, { env });

        // simulate 'backbutton' event triggered by the app
        await testUtils.dom.triggerEvent(document, "backbutton");
        assert.verifySteps(
            ["overrideBackButton: true", "backbutton event"],
            "should have enabled/disabled the back-button override"
        );

        destroy(dummy);
        assert.verifySteps(["overrideBackButton: false"]);
    });

    QUnit.test("multiple components should receive backbutton events in the right order", async function (assert) {
        assert.expect(6);

        patchWithCleanup(mobile.methods, {
            overrideBackButton({ enabled }) {
                assert.step(`overrideBackButton: ${enabled}`);
            },
        });

        class DummyComponent extends Component {
            static template = xml`<div/>`;
            static props = ["*"];
            setup() {
                this._backButtonHandler = useBackButton(this._onBackButton);
            }

            _onBackButton(ev) {
                assert.step(`${this.props.name}: ${ev.type} event`);
                // unmounting is not supported anymore
                // A real business case equivalent to this is to have a Parent component
                // doing a foreach on some reactive object which contains the list of dummy components
                // and calling a callback props.onBackButton right here that removes the element from the list
                destroy(this);
            }
        }

        const props1 = { name: "dummy1" };
        const props2 = { name: "dummy2" };
        const props3 = { name: "dummy3" };
        const target = getFixture();
        const env = makeTestEnv();

        await mount(DummyComponent, target, { props: props1, env });
        await mount(DummyComponent, target, { props: props2, env });
        await mount(DummyComponent, target, { props: props3, env });

        // simulate 'backbutton' events triggered by the app
        await testUtils.dom.triggerEvent(document, "backbutton");
        await testUtils.dom.triggerEvent(document, "backbutton");
        await testUtils.dom.triggerEvent(document, "backbutton");

        assert.verifySteps([
            "overrideBackButton: true",
            "dummy3: backbutton event",
            "dummy2: backbutton event",
            "dummy1: backbutton event",
            "overrideBackButton: false",
        ]);

    });

    QUnit.test("component should receive a backbutton event: custom activation", async function (assert) {
        assert.expect(10);

        patchWithCleanup(mobile.methods, {
            overrideBackButton({ enabled }) {
                assert.step(`overrideBackButton: ${enabled}`);
            },
        });

        class DummyComponent extends Component {
            static template = xml`<button class="dummy" t-esc="state.show" t-on-click="toggle"/>`;
            static props = ["*"];
            setup() {
                this._backButtonHandler = useBackButton(
                    this._onBackButton,
                    this.shouldActivateBackButton.bind(this)
                );
                this.state = useState({
                    show: this.props.show,
                });
            }

            toggle() {
                this.state.show = !this.state.show;
            }

            shouldActivateBackButton() {
                return this.state.show;
            }

            _onBackButton(ev) {
                assert.step(`${ev.type} event`);
            }
        }

        const target = getFixture();
        const env = makeTestEnv();

        const dummy = await mount(DummyComponent, target, { props: { show: false }, env });

        assert.verifySteps([], "shouldn't have enabled backbutton mount");
        await testUtils.dom.click(target.querySelector(".dummy"));
        // simulate 'backbutton' event triggered by the app
        await testUtils.dom.triggerEvent(document, "backbutton");
        await testUtils.dom.click(target.querySelector(".dummy"));
        assert.verifySteps(
            [
                "overrideBackButton: true",
                "backbutton event",
                "overrideBackButton: false",
            ],
            "should have enabled/disabled the back-button override"
        );
        destroy(dummy);

        // enabled at mount
        const dummy2 = await mount(DummyComponent, target, { props: { show: true }, env });
        assert.verifySteps(
            ["overrideBackButton: true"],
            "shouldn have enabled backbutton at mount"
        );
        // simulate 'backbutton' event triggered by the app
        await testUtils.dom.triggerEvent(document, "backbutton");
        destroy(dummy2);

        assert.verifySteps(
            ["backbutton event", "overrideBackButton: false"],
            "should have disabled the back-button override during unmount"
        );
    });

    QUnit.module("Popover");

    QUnit.test("popover is closable with backbutton event", async function (assert) {
        const mainComponents = registry.category("main_components");

        class PseudoWebClient extends Component {
            static template = xml`
                <div>
                    <div id="anchor">Anchor</div>
                    <div id="close">Close</div>
                    <div id="sibling">Sibling</div>
                    <div>
                        <t t-foreach="Components" t-as="C" t-key="C[0]">
                            <t t-component="C[1].Component" t-props="C[1].props"/>
                        </t>
                    </div>
                </div>
            `;
            static props = ["*"];
            setup() {
                this.Components = mainComponents.getEntries();
            }
        }

        const fixture = getFixture();
        const env = await makeTestEnv();
        await mount(PseudoWebClient, fixture, { env });
        const popoverTarget = fixture.querySelector("#anchor");

        patchWithCleanup(mobile.methods, {
            overrideBackButton({ enabled }) {
                assert.step(`overrideBackButton: ${enabled}`);
            },
        });

        class Comp extends Component {
            static template = xml`<div id="comp">in popover</div>`;
            static props = ["*"];
        }

        env.services.popover.add(popoverTarget, Comp, {});
        await nextTick();

        assert.containsOnce(fixture, ".o_popover");
        assert.containsOnce(fixture, ".o_popover #comp");
        assert.verifySteps(["overrideBackButton: true"]);

        // simulate 'backbutton' event triggered by the app
        await testUtils.dom.triggerEvent(document, "backbutton");

        assert.verifySteps(["overrideBackButton: false"]);
        assert.containsNone(fixture, ".o_popover");
        assert.containsNone(fixture, ".o_popover #comp");
    });

    QUnit.module("UpdateDeviceAccountControllerMixin");

    QUnit.test("controller should call native updateAccount method when saving record", async function (assert) {
        assert.expect(4);
        patchWithCleanup(mobile.methods, {
            updateAccount( options ) {
                const { avatar, name, username } = options;
                assert.ok("should call updateAccount");
                assert.ok(avatar.startsWith(BASE64_PNG_HEADER), "should have a PNG base64 encoded avatar");
                assert.strictEqual(name, "Marc Demo");
                assert.strictEqual(username, "demo");
                return Promise.resolve();
            }
        });

        patchUserWithCleanup({ login: "demo", name: "Marc Demo" });

        patchWithCleanup(accountMethodsForMobile, {
            url(path) {
                if (path === '/web/image') {
                    return `data:image/png;base64,${MY_IMAGE}`;
                }
                return super.url(...arguments);
            },
        });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData: serverData,
            arch: `
                <form js_class="res_users_preferences_form">
                    <sheet>
                        <field name="name"/>
                    </sheet>
                </form>`,
        });
        await clickSave(target);
    });

    QUnit.test("controller should call native updateAccount method with SVG avatar when saving record", async function (assert) {
        assert.expect(4);

        patchWithCleanup(mobile.methods, {
            updateAccount( options ) {
                const { avatar, name, username } = options;
                assert.ok("should call updateAccount");
                assert.ok(avatar.startsWith(BASE64_PNG_HEADER), "should have a PNG base64 encoded avatar");
                assert.strictEqual(name, "Marc Demo");
                assert.strictEqual(username, "demo");
                return Promise.resolve();
            }
        });

        patchUserWithCleanup({ login: "demo", name: "Marc Demo" });

        patchWithCleanup(accountMethodsForMobile, {
            url(path) {
                if (path === '/web/image') {
                    return `data:image/svg+xml;base64,${BASE64_SVG_IMAGE}`;
                }
                return super.url(...arguments);
            },
        });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData: serverData,
            arch: `
                <form js_class="res_users_preferences_form">
                    <sheet>
                        <field name="name"/>
                    </sheet>
                </form>`,
        });

        await clickSave(target);
    });

    QUnit.test("UserPreferencesFormView should call native updateAccount method when saving record", async function (assert) {
        assert.expect(4);

        patchWithCleanup(mobile.methods, {
            updateAccount( options ) {
                const { avatar, name, username } = options;
                assert.ok("should call updateAccount");
                assert.ok(avatar.startsWith(BASE64_PNG_HEADER), "should have a PNG base64 encoded avatar");
                assert.strictEqual(name, "Marc Demo");
                assert.strictEqual(username, "demo");
                return Promise.resolve();
            }
        });

        patchUserWithCleanup({ login: "demo", name: "Marc Demo" });

        patchWithCleanup(accountMethodsForMobile, {
            url(path) {
                if (path === '/web/image') {
                    return `data:image/png;base64,${MY_IMAGE}`;
                }
                return super.url(...arguments);
            },
        });

        await makeView({
            type: "form",
            resModel: "users",
            serverData: serverData,
            arch: `
                <form js_class="res_users_preferences_form">
                    <sheet>
                        <field name="name"/>
                    </sheet>
                </form>`,
        });

        await clickSave(target);
    });
});
