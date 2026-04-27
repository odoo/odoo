/** @odoo-module **/

import { ormService } from "@web/core/orm_service";
import { registry } from "@web/core/registry";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { click, getFixture, mount } from "@web/../tests/helpers/utils";
import { IconCreator } from "@web_studio/client_action/icon_creator/icon_creator";

const sampleIconUrl = "/web/Parent.src/img/default_icon_app.png";

QUnit.module("Studio", (hooks) => {
    hooks.beforeEach(() => {
        registry.category("services").add("orm", ormService);
        const fakeHTTPService = {
            start() {
                return {
                    post: () => {},
                };
            },
        };
        registry.category("services").add("http", fakeHTTPService);
    });

    QUnit.module("IconCreator");

    QUnit.test("icon creator: with initial web icon data", async (assert) => {
        assert.expect(5);

        const notificationService = {
            start() {
                return { add: () => {} };
            },
        };
        registry.category("services").add("notification", notificationService, { force: true });

        const target = getFixture();
        await mount(IconCreator, target, {
            props: {
                editable: true,
                type: "base64",
                webIconData: sampleIconUrl,
                onIconChange(icon) {
                    // default values
                    assert.step("icon-changed");
                    assert.deepEqual(icon, {
                        backgroundColor: "#FFFFFF",
                        color: "#00CEB3",
                        iconClass: "fa fa-home",
                        type: "custom_icon",
                    });
                },
            },
            env: await makeTestEnv(),
        });

        assert.strictEqual(
            target.querySelector(".o_web_studio_uploaded_image").style.backgroundImage,
            `url("${sampleIconUrl}")`,
            "displayed image should prioritize web icon data"
        );

        // click on first link: "Design icon"
        await click(target.querySelector(".o_web_studio_upload a"));

        assert.verifySteps(["icon-changed"]);
        assert.strictEqual(
            target.querySelector(".o_web_studio_upload input").accept,
            "image/png",
            "Input should now only accept pngs"
        );
    });

    QUnit.test("icon creator: without initial web icon data", async (assert) => {
        assert.expect(3);

        const target = getFixture();
        await mount(IconCreator, target, {
            props: {
                backgroundColor: "rgb(255, 0, 128)",
                color: "rgb(0, 255, 0)",
                editable: false,
                iconClass: "fa fa-heart",
                type: "custom_icon",
                onIconChange: () => {},
            },
            env: await makeTestEnv(),
        });

        // Attributes should be correctly set
        assert.strictEqual(
            target.querySelector(".o_app_icon").style.backgroundColor,
            "rgb(255, 0, 128)"
        );
        assert.strictEqual(target.querySelector(".o_app_icon i").style.color, "rgb(0, 255, 0)");
        assert.hasClass(target.querySelector(".o_app_icon i"), "fa fa-heart");
    });
});
