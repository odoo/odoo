/** @odoo-module **/

import { IconCreator } from "@web_studio/client_action/icon_creator/icon_creator";
import { StudioHomeMenu } from "@web_studio/client_action/studio_home_menu/studio_home_menu";
import { MODES } from "@web_studio/studio_service";

import { ormService } from "@web/core/orm_service";
import { enterpriseSubscriptionService } from "@web_enterprise/webclient/home_menu/enterprise_subscription_service";

import { fakeCommandService, makeFakeRPCService } from "@web/../tests/helpers/mock_services";
import { userService } from "@web/core/user_service";
import { uiService } from "@web/core/ui/ui_service";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { click, getFixture, mount } from "@web/../tests/helpers/utils";
import { dialogService } from "@web/core/dialog/dialog_service";
import { registry } from "@web/core/registry";

import { Component, EventBus, xml } from "@odoo/owl";
const serviceRegistry = registry.category("services");

const genericHomeMenuProps = {
    apps: [
        {
            actionID: 121,
            id: 1,
            appID: 1,
            label: "Discuss",
            parents: "",
            webIcon: "mail,static/description/icon.png",
            webIconData: "/web_enterprise/static/img/default_icon_app.png",
            xmlid: "app.1",
        },
        {
            actionID: 122,
            id: 2,
            appID: 2,
            label: "Calendar",
            parents: "",
            webIcon: {
                backgroundColor: "#C6572A",
                color: "#FFFFFF",
                iconClass: "fa fa-diamond",
            },
            xmlid: "app.2",
        },
        {
            actionID: 123,
            id: 3,
            appID: 3,
            label: "Contacts",
            parents: "",
            webIcon: false,
            webIconData: "/web_enterprise/static/img/default_icon_app.png",
            xmlid: "app.3",
        },
    ],
};

// -----------------------------------------------------------------------------
// Helpers
// -----------------------------------------------------------------------------

const createStudioHomeMenu = async () => {
    class Parent extends Component {
        get OverlayContainer() {
            return registry.category("main_components").get("OverlayContainer");
        }
    }
    Parent.components = { StudioHomeMenu };
    Parent.template = xml`
        <div>
            <StudioHomeMenu t-props="props.homeMenuProps" />
            <div class="o_dialog_container" />
            <t t-component="OverlayContainer.Component" t-props="OverlayContainer.props" />
        </div>`;

    const env = await makeTestEnv();
    const target = getFixture();
    await mount(Parent, target, { env, props: { homeMenuProps: { ...genericHomeMenuProps } } });
    return target;
};

// -----------------------------------------------------------------------------
// Tests
// -----------------------------------------------------------------------------

let bus;

QUnit.module("Studio", (hooks) => {
    hooks.beforeEach(() => {
        IconCreator.enableTransitions = false;
        registerCleanup(() => {
            IconCreator.enableTransitions = true;
        });
        bus = new EventBus();
        const fakeHomeMenuService = {
            start() {
                return {
                    toggle() {},
                };
            },
        };
        const fakeMenuService = {
            start() {
                return {
                    setCurrentMenu(menu) {
                        bus.trigger("menu:setCurrentMenu", menu.id);
                    },
                    reload() {
                        bus.trigger("menu:reload");
                    },
                    getMenu() {
                        return {};
                    },
                };
            },
        };
        const fakeStudioService = {
            start() {
                return {
                    MODES,
                    open(...args) {
                        bus.trigger("studio:open", args);
                    },
                };
            },
        };
        const fakeHTTPService = {
            start() {
                return {};
            },
        };

        serviceRegistry.add("orm", ormService);
        serviceRegistry.add("enterprise_subscription", enterpriseSubscriptionService);
        serviceRegistry.add("home_menu", fakeHomeMenuService);
        serviceRegistry.add("http", fakeHTTPService);
        serviceRegistry.add("menu", fakeMenuService);
        serviceRegistry.add("user", userService);
        serviceRegistry.add("studio", fakeStudioService);
        serviceRegistry.add("hotkey", hotkeyService);
        serviceRegistry.add("dialog", dialogService);
        serviceRegistry.add("ui", uiService);
        serviceRegistry.add("command", fakeCommandService);
    });

    QUnit.module("StudioHomeMenu");

    QUnit.test("simple rendering", async (assert) => {
        assert.expect(20);

        const target = await createStudioHomeMenu();

        // Main div
        assert.containsOnce(target, ".o_home_menu");

        // Hidden elements
        assert.isNotVisible(
            target.querySelector(".database_expiration_panel"),
            "Expiration panel should not be visible"
        );

        // App list
        assert.containsOnce(target, "div.o_apps");
        assert.containsN(
            target,
            "div.o_apps > div.o_draggable > a.o_app.o_menuitem",
            4,
            "should contain 3 normal app icons + the new app button"
        );

        // App with image
        const firstApp = target.querySelector("div.o_apps > div.o_draggable > a.o_app.o_menuitem");
        assert.strictEqual(firstApp.dataset.menuXmlid, "app.1");
        assert.containsOnce(firstApp, "img.o_app_icon");
        assert.strictEqual(
            firstApp.querySelector("img.o_app_icon").dataset.src,
            "/web_enterprise/static/img/default_icon_app.png"
        );
        assert.containsOnce(firstApp, "div.o_caption");
        assert.strictEqual(firstApp.querySelector("div.o_caption").innerText, "Discuss");
        assert.containsOnce(firstApp, ".o_web_studio_edit_icon i");

        // App with custom icon
        const secondApp = target.querySelectorAll(
            "div.o_apps > div.o_draggable > a.o_app.o_menuitem"
        )[1];
        assert.strictEqual(secondApp.dataset.menuXmlid, "app.2");
        assert.containsOnce(secondApp, "div.o_app_icon");
        assert.strictEqual(
            secondApp.querySelector("div.o_app_icon").style.backgroundColor,
            "rgb(198, 87, 42)",
            "Icon background color should be #C6572A"
        );
        assert.containsOnce(secondApp, "i.fa.fa-diamond");
        assert.strictEqual(
            secondApp.querySelector("i.fa.fa-diamond").style.color,
            "rgb(255, 255, 255)",
            "Icon color should be #FFFFFF"
        );
        assert.containsOnce(secondApp, ".o_web_studio_edit_icon i");

        // New app button
        assert.containsOnce(
            target,
            "div.o_apps > div.o_draggable > a.o_app.o_web_studio_new_app",
            'should contain a "New App icon"'
        );
        const newApp = target.querySelector("a.o_app.o_web_studio_new_app");
        assert.strictEqual(
            newApp.querySelector("img.o_app_icon").dataset.src,
            "/web_studio/static/src/img/default_icon_app.png",
            "Image source URL should end with '/web_studio/static/src/img/default_icon_app.png'"
        );
        assert.containsOnce(newApp, "div.o_caption");
        assert.strictEqual(newApp.querySelector("div.o_caption").innerText, "New App");
    });

    QUnit.test("Click on a normal App", async (assert) => {
        assert.expect(2);

        bus.addEventListener("studio:open", (ev) => {
            assert.deepEqual(ev.detail, [MODES.EDITOR, 121]);
        });
        bus.addEventListener("menu:setCurrentMenu", (ev) => {
            assert.strictEqual(ev.detail, 1);
        });
        const target = await createStudioHomeMenu();

        await click(target.querySelector(".o_menuitem"));
    });

    QUnit.test("Click on new App", async (assert) => {
        assert.expect(1);

        bus.addEventListener("studio:open", (ev) => {
            assert.strictEqual(ev.detail[0], MODES.APP_CREATOR);
        });
        bus.addEventListener("menu:setCurrentMenu", () => {
            throw new Error("should not update the current menu");
        });
        const target = await createStudioHomeMenu();

        await click(target, "a.o_app.o_web_studio_new_app");
    });

    QUnit.test("Click on edit icon button", async (assert) => {
        assert.expect(11);

        const target = await createStudioHomeMenu();

        // TODO: we should maybe check icon visibility comes on mouse over
        const firstEditIconButton = target.querySelector(".o_web_studio_edit_icon i");
        await click(firstEditIconButton);

        const dialog = document.querySelector("div.modal");
        assert.containsOnce(dialog, "header.modal-header");
        assert.strictEqual(
            dialog.querySelector("header.modal-header h4").innerText,
            "Edit Application Icon"
        );

        assert.containsOnce(
            dialog,
            ".modal-content.o_web_studio_edit_menu_icon_modal .o_web_studio_icon_creator"
        );

        assert.containsOnce(dialog, "footer.modal-footer");
        assert.containsN(dialog, "footer button", 2);

        const buttons = dialog.querySelectorAll("footer button");
        const firstButton = buttons[0];
        const secondButton = buttons[1];

        assert.strictEqual(firstButton.innerText, "Confirm");
        assert.hasClass(firstButton, "btn-primary");

        assert.strictEqual(secondButton.innerText, "Cancel");
        assert.hasClass(secondButton, "btn-secondary");

        await click(secondButton);

        assert.strictEqual(document.querySelector("div.modal"), null);

        await click(firstEditIconButton);
        await click(document.querySelector("footer button"));

        assert.strictEqual(document.querySelector("div.modal"), null);
    });

    QUnit.test("edit an icon", async (assert) => {
        assert.expect(3);

        const mockRPC = (route, args) => {
            if (route === "/web_studio/edit_menu_icon") {
                assert.deepEqual(args, {
                    context: {
                        lang: "en",
                        tz: "taht",
                        uid: 7,
                    },
                    icon: ["fa fa-balance-scale", "#f1c40f", "#34495e"],
                    menu_id: 1,
                });
            }
        };
        registry.category("services").add("rpc", makeFakeRPCService(mockRPC), { force: true });

        const target = await createStudioHomeMenu();

        await click(target.querySelector(".o_web_studio_edit_icon i"));
        const dialog = document.querySelector("div.modal");
        await click(dialog.querySelector(".o_web_studio_upload a"));

        assert.doesNotHaveClass(
            dialog.querySelector(".o_web_studio_icon .o_app_icon i"),
            "fa-balance-scale"
        );

        // Change the icon's pictogram
        await click(dialog.querySelectorAll(".o_web_studio_selector")[2]);
        await click(dialog, ".o_web_studio_selector .fa.fa-balance-scale");

        assert.hasClass(
            dialog.querySelector(".o_web_studio_icon .o_app_icon i"),
            "fa-balance-scale"
        );

        await click(dialog.querySelector("footer button")); // trigger save
    });
});
