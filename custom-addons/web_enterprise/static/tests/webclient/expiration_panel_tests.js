/** @odoo-module **/

import { makeFakeNotificationService } from "@web/../tests/helpers/mock_services";
import {
    click,
    getFixture,
    nextTick,
    patchDate,
    patchWithCleanup,
} from "@web/../tests/helpers/utils";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";
import { browser } from "@web/core/browser/browser";
import { ormService } from "@web/core/orm_service";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { enterpriseSubscriptionService } from "@web_enterprise/webclient/home_menu/enterprise_subscription_service";
import { homeMenuService } from "@web_enterprise/webclient/home_menu/home_menu_service";
import testUtils from "@web/../tests/legacy/helpers/test_utils";

const serviceRegistry = registry.category("services");

let target;

async function createExpirationPanel(params = {}) {
    serviceRegistry.add("orm", ormService);
    serviceRegistry.add("home_menu", homeMenuService);
    serviceRegistry.add(
        "notification",
        makeFakeNotificationService(params.mockNotification || (() => {}))
    );
    patchWithCleanup(session, { ...params.session });
    serviceRegistry.add("enterprise_subscription", enterpriseSubscriptionService);

    const webclient = await createWebClient({
        mockRPC: params.mockRPC,
    });
    if (params.mockLuxonSettings) {
        // Already set in the fake localization service, so it's done here
        patchWithCleanup(luxon.Settings, params.mockLuxonSettings);
    }
    await doAction(webclient, "menu");
    await nextTick(); // wait for url to be updated
    return webclient;
}

QUnit.module("web_enterprise", function ({ beforeEach }) {
    beforeEach(() => {
        target = getFixture();
    });

    QUnit.module("Expiration Panel");

    QUnit.test("Expiration Panel one app installed", async function (assert) {
        assert.expect(3);

        patchDate(2019, 9, 10, 12, 0, 0);

        await createExpirationPanel({
            session: {
                expiration_date: "2019-11-09 12:00:00",
                expiration_reason: "",
                notification_type: true, // used by subscription service to know whether mail is installed
                warning: "admin",
            },
        });

        assert.strictEqual(
            target.querySelector(".oe_instance_register").innerText,
            "This database will expire in 1 month."
        );

        // Color should be grey
        assert.hasClass(target.querySelector(".database_expiration_panel"), "alert-info");

        // Close the expiration panel
        await click(target.querySelector(".oe_instance_hide_panel"));

        assert.containsNone(target, ".database_expiration_panel");
    });

    QUnit.test("Expiration Panel one app installed, buy subscription", async function (assert) {
        assert.expect(6);

        patchDate(2019, 9, 10, 12, 0, 0);

        await createExpirationPanel({
            session: {
                expiration_date: "2019-10-24 12:00:00",
                expiration_reason: "demo",
                notification_type: true, // used by subscription service to know whether mail is installed
                warning: "admin",
            },
            mockRPC(route) {
                if (route === "/web/dataset/call_kw/res.users/search_count") {
                    return 7;
                }
            },
        });

        assert.strictEqual(
            target.querySelector(".oe_instance_register").innerText,
            "This demo database will expire in 14 days. Register your subscription or buy a subscription."
        );

        assert.hasClass(
            target.querySelector(".database_expiration_panel"),
            "alert-warning",
            "Color should be orange"
        );
        assert.containsOnce(
            target,
            ".oe_instance_register_show",
            "Part 'Register your subscription'"
        );
        assert.containsOnce(target, ".oe_instance_buy", "Part 'buy a subscription'");
        assert.containsNone(
            target,
            ".oe_instance_register_form",
            "There should be no registration form"
        );

        // Click on 'buy subscription'
        await click(target.querySelector(".oe_instance_buy"));

        assert.strictEqual(
            browser.location,
            "https://www.odoo.com/odoo-enterprise/upgrade?num_users=7"
        );
    });

    QUnit.test(
        "Expiration Panel one app installed, try several times to register subscription",
        async function (assert) {
            assert.expect(44);

            patchDate(2019, 9, 10, 12, 0, 0);

            let callToGetParamCount = 0;

            await createExpirationPanel({
                session: {
                    expiration_date: "2019-10-15 12:00:00",
                    expiration_reason: "trial",
                    notification_type: true, // used by subscription service to know whether mail is installed
                    warning: "admin",
                },
                mockNotification(message, options) {
                    assert.step(JSON.stringify({ message, options }));
                },
                mockRPC(route, { args }) {
                    if (route === "/web/dataset/call_kw/ir.config_parameter/get_param") {
                        assert.step("get_param");
                        if (args[0] === "database.already_linked_subscription_url") {
                            return false;
                        }
                        if (args[0] === "database.already_linked_email") {
                            return "super_company_admin@gmail.com";
                        }
                        assert.strictEqual(args[0], "database.expiration_date");
                        callToGetParamCount++;
                        if (callToGetParamCount <= 3) {
                            return "2019-10-15 12:00:00";
                        } else {
                            return "2019-11-15 12:00:00";
                        }
                    }
                    if (route === "/web/dataset/call_kw/ir.config_parameter/set_param") {
                        assert.step("set_param");
                        assert.strictEqual(args[0], "database.enterprise_code");
                        if (callToGetParamCount === 1) {
                            assert.strictEqual(args[1], "ABCDEF");
                        } else {
                            assert.strictEqual(args[1], "ABC");
                        }
                        return true;
                    }
                    if (
                        route ===
                        "/web/dataset/call_kw/publisher_warranty.contract/update_notification"
                    ) {
                        assert.step("update_notification");
                        assert.ok(args[0] instanceof Array && args[0].length === 0);
                        return true;
                    }
                },
            });

            assert.strictEqual(
                target.querySelector(".oe_instance_register").innerText,
                "This database will expire in 5 days. Register your subscription or buy a subscription."
            );

            assert.hasClass(
                target.querySelector(".database_expiration_panel"),
                "alert-danger",
                "Color should be red"
            );

            assert.containsOnce(
                target,
                ".oe_instance_register_show",
                "Part 'Register your subscription'"
            );
            assert.containsOnce(target, ".oe_instance_buy", "Part 'buy a subscription'");
            assert.containsNone(
                target,
                ".oe_instance_register_form",
                "There should be no registration form"
            );

            // Click on 'register your subscription'
            await click(target.querySelector(".oe_instance_register_show"));

            assert.containsOnce(
                target,
                ".oe_instance_register_form",
                "there should be a registration form"
            );
            assert.containsOnce(
                target,
                '.oe_instance_register_form input[placeholder="Paste code here"]',
                "with an input with place holder 'Paste code here'"
            );
            assert.containsOnce(
                target,
                ".oe_instance_register_form button",
                "and a button 'Register'"
            );
            assert.strictEqual(
                target.querySelector(".oe_instance_register_form button").innerText,
                "Register"
            );

            await click(target.querySelector(".oe_instance_register_form button"));

            assert.containsOnce(
                target,
                ".oe_instance_register_form",
                "there should be a registration form"
            );
            assert.containsOnce(
                target,
                '.oe_instance_register_form input[placeholder="Paste code here"]',
                "with an input with place holder 'Paste code here'"
            );
            assert.containsOnce(
                target,
                ".oe_instance_register_form button",
                "and a button 'Register'"
            );

            await testUtils.fields.editInput(
                target.querySelector(".oe_instance_register_form input"),
                "ABCDEF"
            );
            await click(target.querySelector(".oe_instance_register_form button"));

            assert.strictEqual(
                target.querySelector(".oe_instance_register").innerText,
                "Something went wrong while registering your database. You can try again or contact Odoo Support."
            );
            assert.hasClass(
                target.querySelector(".database_expiration_panel"),
                "alert-danger",
                "Color should be red"
            );
            assert.containsOnce(target, "span.oe_instance_error");
            assert.containsOnce(
                target,
                ".oe_instance_register_form",
                "there should be a registration form"
            );
            assert.containsOnce(
                target,
                '.oe_instance_register_form input[placeholder="Paste code here"]',
                "with an input with place holder 'Paste code here'"
            );
            assert.containsOnce(
                target,
                ".oe_instance_register_form button",
                "and a button 'Register'"
            );
            assert.strictEqual(
                target.querySelector(".oe_instance_register_form button").innerText,
                "Retry"
            );

            await testUtils.fields.editInput(
                target.querySelector(".oe_instance_register_form input"),
                "ABC"
            );
            await click(target.querySelector(".oe_instance_register_form button"));

            assert.containsNone(
                target,
                ".database_expiration_panel",
                "expiration panel should be gone"
            );

            assert.verifySteps([
                // second try to submit
                "get_param",
                "set_param",
                "update_notification",
                "get_param",
                "get_param",
                "get_param",
                // third try
                "get_param",
                "set_param",
                "update_notification",
                "get_param",
                "get_param",
                "get_param",
                `{"message":"Thank you, your registration was successful! Your database is valid until November 15, 2019.","options":{"type":"success"}}`,
            ]);
        }
    );

    QUnit.test(
        "Expiration Panel one app installed, subscription already linked",
        async function (assert) {
            assert.expect(12);

            patchDate(2019, 9, 10, 12, 0, 0);

            // There are some line breaks mismatches between local and runbot test instances.
            // Since they don't affect the layout and we're only interested in the text itself,
            // we normalize whitespaces and line breaks from both the expected and end result
            const formatWhiteSpaces = (text) =>
                text
                    .split(/[\n\s]/)
                    .filter((w) => w !== "")
                    .join(" ");

            let getExpirationDateCount = 0;

            await createExpirationPanel({
                session: {
                    expiration_date: "2019-10-15 12:00:00",
                    expiration_reason: "trial",
                    notification_type: true, // used by subscription service to know whether mail is installed
                    warning: "admin",
                },
                mockRPC(route, { method, args }) {
                    if (route === "/web/webclient/load_menus") {
                        return;
                    }
                    if (route === "/already/linked/send/mail/url") {
                        return {
                            result: false,
                            reason: "By design",
                        };
                    }
                    assert.step(method);
                    if (args[0] === "database.expiration_date") {
                        getExpirationDateCount++;
                        if (getExpirationDateCount === 1) {
                            return "2019-10-15 12:00:00";
                        } else {
                            return "2019-11-17 12:00:00";
                        }
                    }
                    if (args[0] === "database.already_linked_subscription_url") {
                        return "www.super_company.com";
                    }
                    if (args[0] === "database.already_linked_send_mail_url") {
                        return "/already/linked/send/mail/url";
                    }
                    if (args[0] === "database.already_linked_email") {
                        return "super_company_admin@gmail.com";
                    }
                    return true;
                },
            });

            assert.strictEqual(
                target.querySelector(".oe_instance_register").innerText,
                "This database will expire in 5 days. Register your subscription or buy a subscription."
            );

            // Click on 'register your subscription'
            await click(target.querySelector(".oe_instance_register_show"));
            await testUtils.fields.editInput(
                target.querySelector(".oe_instance_register_form input"),
                "ABC"
            );
            await click(target.querySelector(".oe_instance_register_form button"));

            assert.strictEqual(
                formatWhiteSpaces(
                    target.querySelector(".oe_instance_register.oe_database_already_linked")
                        .innerText
                ),
                formatWhiteSpaces(
                    `Your subscription is already linked to a database.
Send an email to the subscription owner to confirm the change, enter a new code or buy a subscription.`
                )
            );

            await click(target.querySelector("a.oe_contract_send_mail"));

            assert.hasClass(
                target.querySelector(".database_expiration_panel"),
                "alert-danger",
                "Color should be red"
            );

            assert.strictEqual(
                formatWhiteSpaces(
                    target.querySelector(".oe_instance_register.oe_database_already_linked")
                        .innerText
                ),
                formatWhiteSpaces(
                    `Your subscription is already linked to a database.
                Send an email to the subscription owner to confirm the change, enter a new code or buy a subscription.
                Unable to send the instructions by email, please contact the Odoo Support
                Error reason: By design`
                )
            );

            assert.verifySteps([
                "get_param",
                "set_param",
                "update_notification",
                "get_param",
                "get_param",
                "get_param",
                "get_param",
            ]);
        }
    );

    QUnit.test("One app installed, database expired", async function (assert) {
        assert.expect(8);

        patchDate(2019, 9, 10, 12, 0, 0);

        let callToGetParamCount = 0;

        await createExpirationPanel({
            session: {
                expiration_date: "2019-10-08 12:00:00",
                expiration_reason: "trial",
                notification_type: true, // used by subscription service to know whether mail is installed
                warning: "admin",
            },
            mockRPC(route, { args, method }) {
                if (route === "/web/webclient/load_menus") {
                    return;
                }
                if (method === "get_param") {
                    if (args[0] === "database.already_linked_subscription_url") {
                        return false;
                    }
                    callToGetParamCount++;
                    if (callToGetParamCount === 1) {
                        return "2019-10-09 12:00:00";
                    } else {
                        return "2019-11-09 12:00:00";
                    }
                }
                return true;
            },
        });

        assert.strictEqual(
            target.querySelector(".oe_instance_register").innerText,
            "This database has expired. Register your subscription or buy a subscription."
        );
        assert.containsOnce(target, ".o_blockUI", "UI should be blocked");

        assert.hasClass(
            target.querySelector(".database_expiration_panel"),
            "alert-danger",
            "Color should be red"
        );
        assert.containsOnce(
            target,
            ".oe_instance_register_show",
            "Part 'Register your subscription'"
        );
        assert.containsOnce(target, ".oe_instance_buy", "Part 'buy a subscription'");

        assert.containsNone(target, ".oe_instance_register_form");

        // Click on 'Register your subscription'
        await click(target.querySelector(".oe_instance_register_show"));
        await testUtils.fields.editInput(
            target.querySelector(".oe_instance_register_form input"),
            "ABC"
        );
        await click(target.querySelector(".oe_instance_register_form button"));

        assert.strictEqual(
            target.querySelector(".oe_instance_register").innerText,
            "Thank you, your registration was successful! Your database is valid until November 9, 2019."
        );
        assert.containsNone(target, ".o_blockUI", "UI should no longer be blocked");
    });

    QUnit.test("One app installed, renew", async function (assert) {
        assert.expect(8);

        patchDate(2019, 9, 10, 12, 0, 0);

        await createExpirationPanel({
            session: {
                expiration_date: "2019-10-20 12:00:00",
                expiration_reason: "renewal",
                notification_type: true, // used by subscription service to know whether mail is installed
                warning: "admin",
            },
            mockRPC(route, { args, method }) {
                if (route === "/web/webclient/load_menus") {
                    return;
                }
                if (method === "get_param") {
                    assert.step("get_param");
                    assert.strictEqual(args[0], "database.enterprise_code");
                    return "ABC";
                }
                return true;
            },
        });

        assert.strictEqual(
            target.querySelector(".oe_instance_register").innerText,
            "This database will expire in 10 days. Renew your subscription "
        );

        assert.hasClass(
            target.querySelector(".database_expiration_panel"),
            "alert-warning",
            "Color should be red"
        );
        assert.containsOnce(target, ".oe_instance_renew", "Part 'Register your subscription'");
        assert.containsOnce(
            target,
            "a.check_enterprise_status",
            "there should be a button for status checking"
        );

        assert.containsNone(target, ".oe_instance_register_form");

        // Click on 'Renew your subscription'
        await click(target.querySelector(".oe_instance_renew"));

        assert.verifySteps(["get_param"]);
    });

    QUnit.test("One app installed, check status and get success", async function (assert) {
        assert.expect(6);

        patchDate(2019, 9, 10, 12, 0, 0);

        await createExpirationPanel({
            session: {
                expiration_date: "2019-10-20 12:00:00",
                expiration_reason: "renewal",
                notification_type: true, // used by subscription service to know whether mail is installed
                warning: "admin",
            },
            mockRPC(route, { args, method }) {
                if (route === "/web/webclient/load_menus") {
                    return;
                }
                if (method === "get_param") {
                    assert.step("get_param");
                    assert.strictEqual(args[0], "database.expiration_date");
                    return "2019-10-24 12:00:00";
                }
                if (method === "update_notification") {
                    assert.step("update_notification");
                }
                return true;
            },
        });

        // click on "Refresh subscription status"
        const refreshButton = target.querySelector("a.check_enterprise_status");
        assert.strictEqual(refreshButton.getAttribute("aria-label"), "Refresh subscription status");
        await click(refreshButton);

        assert.strictEqual(
            target.querySelector(".oe_instance_register.oe_subscription_updated").innerText,
            "Your subscription was updated and is valid until October 24, 2019."
        );

        assert.verifySteps(["update_notification", "get_param"]);
    });

    // Why would we want to reload the page when we check the status and it hasn't changed?
    QUnit.skip("One app installed, check status and get page reload", async function (assert) {
        assert.expect(4);

        patchDate(2019, 9, 10, 12, 0, 0);

        await createExpirationPanel({
            session: {
                expiration_date: "2019-10-20 12:00:00",
                expiration_reason: "renewal",
                notification_type: true, // used by subscription service to know whether mail is installed
                warning: "admin",
            },
            mockRPC(route, { method }) {
                if (route === "/web/webclient/load_menus") {
                    return;
                }
                if (method === "get_param") {
                    assert.step("get_param");
                    return "2019-10-20 12:00:00";
                }
                if (method === "update_notification") {
                    assert.step("update_notification");
                }
                return true;
            },
        });

        // click on "Refresh subscription status"
        await click(target.querySelector("a.check_enterprise_status"));

        assert.verifySteps(["update_notification", "get_param", "reloadPage"]);
    });

    QUnit.test("One app installed, upgrade database", async function (assert) {
        assert.expect(6);

        patchDate(2019, 9, 10, 12, 0, 0);

        await createExpirationPanel({
            session: {
                expiration_date: "2019-10-20 12:00:00",
                expiration_reason: "upsell",
                notification_type: true, // used by subscription service to know whether mail is installed
                warning: "admin",
            },
            mockRPC(route, { args, method }) {
                if (route === "/web/webclient/load_menus") {
                    return;
                }
                if (method === "get_param") {
                    assert.step("get_param");
                    assert.strictEqual(args[0], "database.enterprise_code");
                    return "ABC";
                }
                if (method === "search_count") {
                    assert.step("search_count");
                    return 13;
                }
                return true;
            },
        });

        assert.strictEqual(
            target.querySelector(".oe_instance_register").innerText,
            "This database will expire in 10 days. You have more users or more apps installed than your subscription allows.\n" +
                "Upgrade your subscription "
        );

        // click on "Upgrade your subscription"
        await click(target.querySelector("a.oe_instance_upsell"));

        assert.verifySteps(["get_param", "search_count"]);
        assert.strictEqual(
            browser.location,
            "https://www.odoo.com/odoo-enterprise/upsell?num_users=13&contract=ABC"
        );
    });

    QUnit.test("One app installed, message for non admin user", async function (assert) {
        assert.expect(2);

        patchDate(2019, 9, 10, 12, 0, 0);

        await createExpirationPanel({
            session: {
                expiration_date: "2019-11-08 12:00:00",
                expiration_reason: "",
                notification_type: true, // used by subscription service to know whether mail is installed
                warning: "user",
            },
        });

        assert.strictEqual(
            target.querySelector(".oe_instance_register").innerText,
            "This database will expire in 29 days. Log in as an administrator to correct the issue."
        );

        assert.hasClass(
            target.querySelector(".database_expiration_panel"),
            "alert-info",
            "Color should be grey"
        );
    });

    QUnit.test("One app installed, navigation to renewal page", async function (assert) {
        assert.expect(9);

        patchDate(2019, 11, 10, 0, 0, 0);

        await createExpirationPanel({
            session: {
                expiration_date: "2019-10-20 12:00:00",
                expiration_reason: "renewal",
                notification_type: true, // used by subscription service to know whether mail is installed
                warning: "admin",
            },
            mockRPC(route, { args, method }) {
                if (route === "/web/webclient/load_menus") {
                    return;
                }
                if (method === "get_param") {
                    assert.step("get_param");
                    assert.strictEqual(args[0], "database.enterprise_code");
                    return "ABC";
                }
                if (method === "update_notification") {
                    assert.step("update_notification");
                }
                return true;
            },
        });

        assert.strictEqual(
            target.querySelector(".oe_instance_register").innerText,
            "This database has expired. Renew your subscription "
        );

        assert.hasClass(target.querySelector(".database_expiration_panel"), "alert-danger");
        assert.containsOnce(target, ".oe_instance_renew", "Part 'Register your subscription'");
        assert.containsOnce(
            target,
            "a.check_enterprise_status",
            "there should be a button for status checking"
        );

        assert.containsNone(target, ".oe_instance_register_form");

        // Click on 'Renew your subscription'
        await click(target.querySelector(".oe_instance_renew"));

        assert.strictEqual(
            browser.location,
            "https://www.odoo.com/odoo-enterprise/renew?contract=ABC"
        );

        assert.verifySteps(["get_param"]);
    });

    QUnit.test("One app installed, different locale (arabic)", async function (assert) {
        assert.expect(1);

        patchDate(2019, 9, 25, 12, 0, 0);

        await createExpirationPanel({
            session: {
                expiration_date: "2019-10-20 12:00:00",
                expiration_reason: "renewal",
                notification_type: true, // used by subscription service to know whether mail is installed
                warning: "admin",
            },
            mockLuxonSettings: {
                defaultLocale: "ar-001",
                defaultNumberingSystem: "arab",
            },
            async mockRPC(route, { method }) {
                if (route === "/web/webclient/load_menus") {
                    return;
                }
                if (method === "get_param") {
                    return "2019-11-09 12:00:00";
                }
                return true;
            },
        });

        await click(target, ".check_enterprise_status");

        assert.strictEqual(
            target.querySelector(".oe_instance_register").innerText,
            "Your subscription was updated and is valid until ٩ نوفمبر ٢٠١٩."
        );
    });
});
