/** @odoo-module **/

import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { setupViewRegistries } from "@web/../tests/views/helpers";
import { AppCreator } from "@web_studio/client_action/app_creator/app_creator";
import { makeFakeHTTPService } from "@web/../tests/helpers/mock_services";
import {
    click,
    getFixture,
    nextTick,
    triggerEvent,
    editInput,
    patchWithCleanup,
} from "@web/../tests/helpers/utils";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { mountInFixture } from "@web/../tests/helpers/mount_in_fixture";

const serviceRegistry = registry.category("services");
const sampleIconUrl = "/web/Parent.src/img/default_icon_app.png";

function makeFakeUIService({ block = () => {}, unblock = () => {} } = {}) {
    return {
        start(env) {
            const ui = {
                block,
                unblock,
                getActiveElementOf: () => undefined,
            };
            Object.defineProperty(env, "isSmall", {
                get() {
                    return false;
                },
            });
            return ui;
        },
    };
}

async function startAtStep(target, startStep) {
    if (["app", "model", "model_configuration"].includes(startStep)) {
        // From welcome to app
        await click(target, ".o_web_studio_app_creator_next");
    }
    if (["model", "model_configuration"].includes(startStep)) {
        // From app to model
        await editInput(target, "input[name='appName']", "testApp");
        await click(target, ".o_web_studio_app_creator_next");
    }
    if (["model_configuration"].includes(startStep)) {
        // From model to model_configuration
        await editInput(target, "input[name='menuName']", "testMenu");
        await click(target, ".o_web_studio_app_creator_next");
    }
}

async function createAppCreator(params = {}) {
    const onNewAppCreated = params.onNewAppCreated || (() => {});

    for (const serviceKey in params.services) {
        serviceRegistry.add(serviceKey, params.services[serviceKey], { force: true });
    }

    const { mockRPC, serverData, startStep } = params;
    const target = getFixture();
    const component = await mountInFixture(AppCreator, target, {
        props: { onNewAppCreated },
        env: await makeTestEnv({
            serverData,
            mockRPC,
        }),
    });

    if (startStep) {
        await startAtStep(target, startStep);
    }

    return { state: component.state };
}

QUnit.module("AppCreator", (hooks) => {
    let serverData;
    let target;
    hooks.beforeEach(() => {
        target = getFixture();

        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
            clearTimeout: () => {},
        });
        patchWithCleanup(AutoComplete, {
            timeout: 0,
        });

        setupViewRegistries();

        serviceRegistry.add("http", makeFakeHTTPService(), { force: true });
        serviceRegistry.add("ui", makeFakeUIService(), { force: true });

        serverData = {
            models: {
                "ir.model": {
                    fields: {
                        display_name: { type: "char" },
                        transient: { type: "boolean" },
                        abstract: { type: "boolean" },
                    },
                    records: [{ id: 69, display_name: "The Value" }],
                },
            },
        };
    });

    QUnit.test("app creator: standard flow with model creation", async (assert) => {
        assert.expect(37);

        const fakeHttpRequestService = {
            start() {
                return async (route) => {
                    if (route === "/web/binary/upload_attachment") {
                        assert.step(route);
                        return `[{ "id": 666 }]`;
                    }
                };
            },
        };

        const { state } = await createAppCreator({
            serverData,
            services: {
                ui: makeFakeUIService({
                    block: () => assert.step("UI blocked"),
                    unblock: () => assert.step("UI unblocked"),
                }),
                httpRequest: fakeHttpRequestService,
                http: makeFakeHTTPService(null, async (route) => {
                    if (route === "/web/binary/upload_attachment") {
                        assert.step(route);
                        return `[{ "id": 666 }]`;
                    }
                }),
            },
            onNewAppCreated: () => assert.step("new-app-created"),
            mockRPC: async (route, params) => {
                if (typeof route === "object") {
                    assert.strictEqual(route.model, "ir.attachment");
                    return [{ datas: sampleIconUrl }];
                }

                if (route === "/web_studio/create_new_app") {
                    const { app_name, menu_name, model_choice, model_id, model_options } = params;
                    assert.strictEqual(app_name, "Kikou", "App name should be correct");
                    assert.strictEqual(menu_name, "Petite Perruche", "Menu name should be correct");
                    assert.notOk(model_id, "Should not have a model id");
                    assert.strictEqual(model_choice, "new", "Model choice should be 'new'");
                    assert.deepEqual(
                        model_options,
                        ["use_partner", "use_sequence", "use_mail", "use_active"],
                        "Model options should include the defaults and 'use_partner'"
                    );
                    return true;
                }
                if (route === "/web/dataset/call_kw/ir.attachment/read") {
                    assert.strictEqual(params.model, "ir.attachment");
                    return [{ datas: sampleIconUrl }];
                }
            },
        });

        // step: 'welcome'
        assert.strictEqual(state.step, "welcome", "Current step should be welcome");
        assert.containsNone(
            target,
            ".o_web_studio_app_creator_previous",
            "Previous button should not be rendered at step welcome"
        );
        assert.hasClass(
            target.querySelector(".o_web_studio_app_creator_next"),
            "is_ready",
            "Next button should be ready at step welcome"
        );

        // go to step: 'app'
        await click(target, ".o_web_studio_app_creator_next");

        assert.strictEqual(state.step, "app", "Current step should be app");
        assert.containsOnce(
            target,
            ".o_web_studio_icon_creator .o_web_studio_selectors",
            "Icon creator should be rendered in edit mode"
        );

        // Icon creator interactions
        let icon = target.querySelector(".o_app_icon i");

        // Initial state: take default values
        assert.strictEqual(
            target.querySelector(".o_app_icon").style.backgroundColor,
            "rgb(255, 255, 255)",
            "default background color: #FFFFFF"
        );
        assert.strictEqual(icon.style.color, "rgb(0, 206, 179)", "default color: #00CEB3");
        assert.hasClass(icon, "fa fa-home", "default icon class: delicious");

        await click(target.querySelector(".o_web_studio_selector_background > button"));
        assert.containsOnce(target, ".o_select_menu_menu", "the first palette should be open");

        await click(target.querySelector(".o_web_studio_selector_background > button"));
        await click(target.querySelector(".o_web_studio_selector_color > button"));

        assert.containsOnce(
            target,
            ".o_select_menu_menu",
            "opening another palette should close the first"
        );

        await click(target.querySelectorAll(".o_select_menu_menu div")[2]);
        await click(target.querySelector(".o_web_studio_selector_icon > button"));
        await click(target.querySelector(".o_select_menu_item .fa-heart"));

        icon = target.querySelector(".o_app_icon i");

        assert.strictEqual(
            target.querySelector(".o_web_studio_selector_color .o_select_menu_toggler_slot > div")
                .style.backgroundColor,
            "rgb(241, 196, 15)", // translation of #F1C40F
            "color selector should have changed"
        );
        assert.strictEqual(
            icon.style.color,
            "rgb(241, 196, 15)",
            "icon color should also have changed"
        );
        assert.hasClass(
            target.querySelector(".o_web_studio_selector_icon i"),
            "fa fa-heart",
            "class selector should have changed"
        );
        assert.hasClass(icon, "fa fa-heart", "icon class should also have changed");

        // Click and upload on first link: upload a file
        // mimic the event triggered by the upload (jquery)
        // we do not use the triggerEvent helper as it requires the element to be visible,
        // which isn't the case here (and this is valid)
        target.querySelector(".o_web_studio_upload input").dispatchEvent(new Event("change"));
        await nextTick();

        assert.strictEqual(
            state.data.iconData.uploaded_attachment_id,
            666,
            "attachment id should have been given by the RPC"
        );
        assert.strictEqual(
            target.querySelector(".o_web_studio_uploaded_image").style.backgroundImage,
            `url("data:image/png;base64,${sampleIconUrl}")`,
            "icon should take the updated attachment data"
        );

        // try to go to step 'model'
        await click(target, ".o_web_studio_app_creator_next");

        const appNameInput = target.querySelector('input[name="appName"]').parentNode;

        assert.strictEqual(
            state.step,
            "app",
            "Current step should not be update because the input is not filled"
        );
        assert.hasClass(
            appNameInput,
            "o_web_studio_field_warning",
            "Input should be in warning mode"
        );

        await editInput(target, 'input[name="appName"]', "Kikou");
        assert.doesNotHaveClass(
            appNameInput,
            "o_web_studio_field_warning",
            "Input shouldn't be in warning mode anymore"
        );

        // step: 'model'
        await click(target, ".o_web_studio_app_creator_next");

        assert.strictEqual(state.step, "model", "Current step should be model");

        assert.containsNone(
            target,
            ".o_web_studio_selectors",
            "Icon creator should be rendered in readonly mode"
        );

        // try to go to next step
        await click(target, ".o_web_studio_app_creator_next");

        assert.hasClass(
            target.querySelector('input[name="menuName"]').parentNode,
            "o_web_studio_field_warning",
            "Input should be in warning mode"
        );

        await editInput(target, 'input[name="menuName"]', "Petite Perruche");

        // go to next step (model configuration)
        await click(target, ".o_web_studio_app_creator_next");
        assert.strictEqual(
            state.step,
            "model_configuration",
            "Current step should be model_configuration"
        );
        assert.containsOnce(
            target,
            'input[name="use_active"]',
            "Debug options should be visible without debug mode"
        );
        // check an option
        await click(target, 'input[name="use_partner"]');
        assert.containsOnce(
            target,
            'input[name="use_partner"]:checked',
            "Option should have been checked"
        );

        // go back then go forward again
        await click(target, ".o_web_studio_model_configurator_previous");
        await click(target, ".o_web_studio_app_creator_next");
        // options should have been reset
        assert.containsNone(
            target,
            'input[name="use_partner"]:checked',
            "Options should have been reset by going back then forward"
        );

        // check the option again, we want to test it in the RPC
        await click(target, 'input[name="use_partner"]');

        await click(target, ".o_web_studio_model_configurator_next");

        assert.verifySteps([
            "/web/binary/upload_attachment",
            "UI blocked",
            "new-app-created",
            "UI unblocked",
        ]);
    });

    QUnit.test("app creator: has 'lines' options to auto-create a one2many", async (assert) => {
        assert.expect(7);

        await createAppCreator({
            serverData,
            startStep: "model_configuration",
            mockRPC: async (route, params) => {
                if (route === "/web_studio/create_new_app") {
                    const { app_name, menu_name, model_choice, model_id, model_options } = params;
                    assert.strictEqual(app_name, "testApp", "App name should be correct");
                    assert.strictEqual(menu_name, "testMenu", "Menu name should be correct");
                    assert.notOk(model_id, "Should not have a model id");
                    assert.strictEqual(model_choice, "new", "Model choice should be 'new'");
                    assert.deepEqual(
                        model_options,
                        ["lines", "use_sequence", "use_mail", "use_active"],
                        "Model options should include the defaults and 'lines'"
                    );
                    return true;
                }
            },
        });

        assert.containsOnce(
            target,
            ".o_web_studio_model_configurator_option input[type='checkbox'][name='lines'][id='lines']"
        );
        assert.strictEqual(
            target.querySelector("label[for='lines']").textContent,
            "LinesAdd details to your records with an embedded list view"
        );

        await click(
            target,
            ".o_web_studio_model_configurator_option input[type='checkbox'][name='lines']"
        );
        await click(target, ".o_web_studio_model_configurator_next");
    });

    QUnit.test("app creator: debug flow with existing model", async (assert) => {
        assert.expect(17);

        patchWithCleanup(odoo, { debug: "1" });

        const { state } = await createAppCreator({
            serverData,
            startStep: "model",
            async mockRPC(route, params) {
                switch (route) {
                    case "/web/dataset/call_kw/ir.model/name_search": {
                        assert.deepEqual(params.kwargs.args, [
                            "&",
                            "&",
                            ["transient", "=", false],
                            ["abstract", "=", false],
                            "!",
                            ["id", "in", []],
                        ]);
                        assert.step(route);
                        assert.strictEqual(
                            params.model,
                            "ir.model",
                            "request should target the right model"
                        );
                        break;
                    }
                    case "/web_studio/create_new_app": {
                        assert.step(route);
                        assert.strictEqual(
                            params.model_id,
                            69,
                            "model id should be the one provided"
                        );
                        return true;
                    }
                }
            },
        });

        await editInput(target, "input[name='menuName']", "testMenuName");

        let buttonNext = target.querySelector("button.o_web_studio_app_creator_next");
        assert.hasClass(buttonNext, "is_ready");

        await editInput(target, 'input[name="menuName"]', "Petite Perruche");
        // check the 'new model' radio
        await click(target, 'input[name="model_choice"][value="new"]');

        // go to next step (model configuration)
        await click(target, ".o_web_studio_app_creator_next");
        assert.strictEqual(
            state.step,
            "model_configuration",
            "Current step should be model_configuration"
        );
        assert.containsOnce(
            target,
            'input[name="use_active"]',
            "Debug options should be visible in debug mode"
        );
        // go back, we want the 'existing model flow'
        await click(target, ".o_web_studio_model_configurator_previous");

        // since we came back, we need to update our buttonNext ref - the querySelector is not live
        buttonNext = target.querySelector("button.o_web_studio_app_creator_next");

        // check the 'existing model' radio
        await click(target, 'input[name="model_choice"][value="existing"]');

        assert.doesNotHaveClass(
            target.querySelector(".o_web_studio_menu_creator_model"),
            "o_web_studio_field_warning"
        );
        assert.doesNotHaveClass(buttonNext, "is_ready");
        assert.containsOnce(
            target,
            ".o_record_selector",
            "There should be a many2one to select a model"
        );

        await click(buttonNext);
        assert.hasClass(
            target.querySelector(".o_web_studio_menu_creator_model"),
            "o_web_studio_field_warning"
        );
        assert.doesNotHaveClass(buttonNext, "is_ready");

        await editInput(target, ".o_record_selector input", "The");
        await click(target.querySelector(".o-autocomplete--dropdown-item"));

        assert.strictEqual(
            target.querySelector(".o_record_selector input").value,
            "The Value",
            "Correct value should be selected."
        );

        assert.doesNotHaveClass(
            target.querySelector(".o_web_studio_menu_creator_model"),
            "o_web_studio_field_warning"
        );
        assert.hasClass(buttonNext, "is_ready");

        await click(buttonNext);

        assert.verifySteps([
            "/web/dataset/call_kw/ir.model/name_search",
            "/web_studio/create_new_app",
        ]);
    });

    QUnit.test('app creator: navigate through steps using "ENTER"', async (assert) => {
        assert.expect(12);

        const { state } = await createAppCreator({
            serverData,
            services: {
                ui: makeFakeUIService({
                    block: () => assert.step("UI blocked"),
                    unblock: () => assert.step("UI unblocked"),
                }),
            },
            onNewAppCreated: () => assert.step("new-app-created"),
            async mockRPC(route, { app_name, menu_name, model_id }) {
                if (route === "/web_studio/create_new_app") {
                    assert.strictEqual(app_name, "Kikou", "App name should be correct");
                    assert.strictEqual(menu_name, "Petite Perruche", "Menu name should be correct");
                    assert.notOk(model_id, "Should not have a model id");
                    return true;
                }
            },
        });

        // step: 'welcome'
        assert.strictEqual(state.step, "welcome", "Current step should be set to welcome");

        // go to step 'app'
        await triggerEvent(document, null, "keydown", { key: "Enter" });
        assert.strictEqual(state.step, "app", "Current step should be set to app");

        // try to go to step 'model'
        await triggerEvent(document, null, "keydown", { key: "Enter" });
        assert.strictEqual(
            state.step,
            "app",
            "Current step should not be update because the input is not filled"
        );

        await editInput(target, 'input[name="appName"]', "Kikou");

        // go to step 'model'
        await triggerEvent(document, null, "keydown", { key: "Enter" });
        assert.strictEqual(state.step, "model", "Current step should be model");

        // try to create app
        await triggerEvent(document, null, "keydown", { key: "Enter" });
        assert.hasClass(
            target.querySelector('input[name="menuName"]').parentNode,
            "o_web_studio_field_warning",
            "a warning should be displayed on the input"
        );

        await editInput(target, 'input[name="menuName"]', "Petite Perruche");
        await triggerEvent(document, null, "keydown", { key: "Enter" });
        await triggerEvent(document, null, "keydown", { key: "Enter" });

        assert.verifySteps(["UI blocked", "new-app-created", "UI unblocked"]);
    });
});
