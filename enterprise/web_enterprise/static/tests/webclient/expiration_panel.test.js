import { expect, test } from "@odoo/hoot";
import { click, queryFirst, edit } from "@odoo/hoot-dom";
import { animationFrame, mockDate, runAllTimers } from "@odoo/hoot-mock";
import {
    getService,
    mockService,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    serverState,
} from "@web/../tests/web_test_helpers";

import { session } from "@web/session";
import { browser } from "@web/core/browser/browser";
import { WebClientEnterprise } from "@web_enterprise/webclient/webclient";

test("Expiration Panel one app installed", async () => {
    mockDate("2019-10-10T12:00:00");

    patchWithCleanup(session, {
        expiration_date: "2019-11-09 12:00:00",
        expiration_reason: "",
        storeData: true, // used by subscription service to know whether mail is installed
        warning: "admin",
    });
    await mountWithCleanup(WebClientEnterprise);
    await animationFrame();
    await getService("action").doAction("menu");

    expect(".oe_instance_register").toHaveText("This database will expire in 1 month.");

    // Color should be grey
    expect(".database_expiration_panel").toHaveClass("alert-info");

    // Close the expiration panel
    await click(".oe_instance_hide_panel");
    await animationFrame();

    expect(".database_expiration_panel").toHaveCount(0);
});

test("Expiration Panel one app installed, buy subscription", async () => {
    expect.assertions(6);

    mockDate("2019-10-10T12:00:00");
    patchWithCleanup(session, {
        expiration_date: "2019-10-24 12:00:00",
        expiration_reason: "demo",
        storeData: true, // used by subscription service to know whether mail is installed
        warning: "admin",
    });
    onRpc("res.users", "search_count", () => 7);
    await mountWithCleanup(WebClientEnterprise);
    await animationFrame();
    await runAllTimers();

    expect(".oe_instance_register").toHaveText(
        "This demo database will expire in 14 days. Register your subscription or buy a subscription."
    );

    expect(".database_expiration_panel").toHaveClass("alert-warning", {
        message: "Color should be orange",
    });

    expect(".oe_instance_register_show").toHaveCount(1, {
        message: "Part 'Register your subscription'",
    });
    expect(".oe_instance_buy").toHaveCount(1, { message: "Part 'buy a subscription'" });
    expect(".oe_instance_register_form").toHaveCount(0, {
        message: "There should be no registration form",
    });

    // Click on 'buy subscription'
    await click(".oe_instance_buy");
    await animationFrame();

    expect(browser.location.href).toBe("https://www.odoo.com/odoo-enterprise/upgrade?num_users=7");
});

test("Expiration Panel one app installed, try several times to register subscription", async () => {
    expect.assertions(33);

    mockDate("2019-10-10T12:00:00");

    let callToGetParamCount = 0;

    patchWithCleanup(session, {
        expiration_date: "2019-10-15 12:00:00",
        expiration_reason: "trial",
        storeData: true, // used by subscription service to know whether mail is installed
        warning: "admin",
    });

    mockService("notification", {
        add: (message, options) => {
            expect.step(JSON.stringify({ message, options }));
        },
    });
    onRpc("get_param", ({ args }) => {
        expect.step("get_param");
        if (args[0] === "database.already_linked_subscription_url") {
            return false;
        }
        if (args[0] === "database.already_linked_email") {
            return "super_company_admin@gmail.com";
        }
        expect(args[0]).toBe("database.expiration_date");
        callToGetParamCount++;
        if (callToGetParamCount <= 3) {
            return "2019-10-15 12:00:00";
        } else {
            return "2019-11-15 12:00:00";
        }
    });
    onRpc("set_param", ({ args }) => {
        expect.step("set_param");
        expect(args[0]).toBe("database.enterprise_code");
        if (callToGetParamCount === 1) {
            expect(args[1]).toBe("ABCDEF");
        } else {
            expect(args[1]).toBe("ABC");
        }
        return true;
    });
    onRpc("update_notification", ({ args }) => {
        expect.step("update_notification");
        expect(args[0]).toBeInstanceOf(Array);
        expect(args[0]).toHaveLength(0);
        return true;
    });
    onRpc("res.users", "search_count", () => 7);
    await mountWithCleanup(WebClientEnterprise);
    await animationFrame();

    expect(".oe_instance_register").toHaveText(
        "This database will expire in 5 days. Register your subscription or buy a subscription."
    );

    expect(".database_expiration_panel").toHaveClass("alert-danger", {
        message: "Color should be red",
    });

    expect(".oe_instance_register_show").toHaveCount(1, {
        message: "Part 'Register your subscription'",
    });
    expect(".oe_instance_buy").toHaveCount(1, { message: "Part 'buy a subscription'" });
    expect(".oe_instance_register_form").toHaveCount(0, {
        message: "There should be no registration form",
    });

    // Click on 'buy subscription'
    await click(".oe_instance_register_show");
    await animationFrame();

    expect(".oe_instance_register_form").toHaveCount(1, {
        message: "there should be a registration form",
    });
    expect('.oe_instance_register_form input[placeholder="Paste code here"]').toHaveCount(1, {
        message: "with an input with place holder 'Paste code here'",
    });
    expect(".oe_instance_register_form button").toHaveCount(1, {
        message: "and a button 'Register'",
    });
    expect(".oe_instance_register_form button").toHaveText("Register");

    await click(".oe_instance_register_form button");
    await animationFrame();

    expect(".oe_instance_register_form").toHaveCount(1, {
        message: "there should be a registration form",
    });
    expect('.oe_instance_register_form input[placeholder="Paste code here"]').toHaveCount(1, {
        message: "with an input with place holder 'Paste code here'",
    });
    expect(".oe_instance_register_form button").toHaveCount(1, {
        message: "and a button 'Register'",
    });

    await click(".oe_instance_register_form input");
    await edit("ABCDEF");
    await animationFrame();
    await click(".oe_instance_register_form button");
    await animationFrame();

    expect(queryFirst(".oe_instance_register")).toHaveText(
        "Something went wrong while registering your database. You can try again or contact Odoo Support."
    );
    expect(".database_expiration_panel").toHaveClass("alert-danger", {
        message: "Color should be red",
    });
    expect("span.oe_instance_error").toHaveCount(1);
    expect(".oe_instance_register_form").toHaveCount(1, {
        message: "there should be a registration form",
    });
    expect('.oe_instance_register_form input[placeholder="Paste code here"]').toHaveCount(1, {
        message: "with an input with place holder 'Paste code here'",
    });
    expect(".oe_instance_register_form button").toHaveCount(1, {
        message: "and a button 'Register'",
    });
    expect(".oe_instance_register_form button").toHaveText("Retry");

    await click(".oe_instance_register_form input");
    await edit("ABC");
    await animationFrame();
    await click(".oe_instance_register_form button");
    await animationFrame();

    expect(".database_expiration_panel").toHaveCount(0, {
        message: "expiration panel should be gone",
    });

    expect.verifySteps([
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
});

test("Expiration Panel one app installed, subscription already linked", async () => {
    expect.assertions(5);

    mockDate("2019-10-10T12:00:00");

    let getExpirationDateCount = 0;

    patchWithCleanup(session, {
        expiration_date: "2019-10-15 12:00:00",
        expiration_reason: "trial",
        storeData: true, // used by subscription service to know whether mail is installed
        warning: "admin",
    });
    onRpc("/already/linked/send/mail/url", () => ({
        result: false,
        reason: "By design",
    }));
    onRpc("get_param", ({ args }) => {
        expect.step("get_param");
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
    });
    onRpc("set_param", () => {
        expect.step("set_param");
        return true;
    });
    onRpc("update_notification", () => {
        expect.step("update_notification");
        return true;
    });
    await mountWithCleanup(WebClientEnterprise);
    await animationFrame();

    expect(".oe_instance_register").toHaveText(
        "This database will expire in 5 days. Register your subscription or buy a subscription."
    );
    // Click on 'register your subscription'
    await click(".oe_instance_register_show");
    await animationFrame();
    await click(".oe_instance_register_form input");
    await edit("ABC");
    await click(".oe_instance_register_form button");
    await animationFrame();

    expect(".oe_instance_register.oe_database_already_linked").toHaveText(
        `Your subscription is already linked to a database.\nSend an email to the subscription owner to confirm the change, enter a new code or buy a subscription.`
    );

    await click("a.oe_contract_send_mail");
    await animationFrame();
    expect(".database_expiration_panel").toHaveClass("alert-danger", {
        message: "Color should be red",
    });

    expect(".oe_instance_register.oe_database_already_linked").toHaveText(
        `Your subscription is already linked to a database.\nSend an email to the subscription owner to confirm the change, enter a new code or buy a subscription.\n\nUnable to send the instructions by email, please contact the Odoo Support\nError reason: By design`
    );

    expect.verifySteps([
        "get_param",
        "set_param",
        "update_notification",
        "get_param",
        "get_param",
        "get_param",
        "get_param",
    ]);
});

test("One app installed, database expired", async () => {
    expect.assertions(8);

    mockDate("2019-10-10T12:00:00");

    let callToGetParamCount = 0;

    patchWithCleanup(session, {
        expiration_date: "2019-10-08 12:00:00",
        expiration_reason: "trial",
        storeData: true, // used by subscription service to know whether mail is installed
        warning: "admin",
    });
    onRpc("/already/linked/send/mail/url", () => ({
        result: false,
        reason: "By design",
    }));
    onRpc("get_param", ({ args }) => {
        if (args[0] === "database.already_linked_subscription_url") {
            return false;
        }
        callToGetParamCount++;
        if (callToGetParamCount === 1) {
            return "2019-10-09 12:00:00";
        } else {
            return "2019-11-09 12:00:00";
        }
    });
    onRpc("set_param", () => true);
    onRpc("update_notification", () => true);
    await mountWithCleanup(WebClientEnterprise);
    await animationFrame();

    expect(".oe_instance_register").toHaveText(
        "This database has expired. Register your subscription or buy a subscription."
    );
    expect(".o_blockUI").toHaveCount(1, { message: "UI should be blocked" });

    expect(".database_expiration_panel").toHaveClass("alert-danger", {
        message: "Color should be red",
    });
    expect(".oe_instance_register_show").toHaveCount(1, {
        message: "Part 'Register your subscription'",
    });
    expect(".oe_instance_buy").toHaveCount(1, { message: "Part 'buy a subscription'" });

    expect(".oe_instance_register_form").toHaveCount(0);

    // Click on 'Register your subscription'
    await click(".oe_instance_register_show");
    await animationFrame();
    await click(".oe_instance_register_form input");
    await edit("ABC");
    await click(".oe_instance_register_form button");
    await animationFrame();

    expect(".oe_instance_register").toHaveText(
        "Thank you, your registration was successful! Your database is valid until November 9, 2019."
    );
    expect(".o_blockUI").toHaveCount(0, { message: "UI should no longer be blocked" });
});

test("One app installed, renew", async () => {
    expect.assertions(7);

    mockDate("2019-10-10T12:00:00");

    patchWithCleanup(session, {
        expiration_date: "2019-10-20 12:00:00",
        expiration_reason: "renewal",
        storeData: true, // used by subscription service to know whether mail is installed
        warning: "admin",
    });
    onRpc("get_param", ({ args }) => {
        expect.step("get_param");
        expect(args[0]).toBe("database.enterprise_code");
        return "ABC";
    });
    await mountWithCleanup(WebClientEnterprise);
    await animationFrame();

    expect(".oe_instance_register").toHaveText(
        "Your subscription expired 9 days ago. This database will be blocked soon.\n" +
            "Renew now\n" +
            "I paid, please recheck!"
    );

    expect(".database_expiration_panel").toHaveClass("alert-warning", {
        message: "Color should be orange",
    });
    expect(".oe_instance_renew").toHaveCount(1, { message: "Part 'Register your subscription'" });
    expect("a.check_enterprise_status").toHaveCount(1, {
        message: "there should be a button for status checking",
    });

    expect(".oe_instance_register_form").toHaveCount(0);

    // Click on 'Renew your subscription'
    await click(".oe_instance_renew");
    await animationFrame();

    expect.verifySteps(["get_param"]);
});

test("One app installed, check status and get success", async () => {
    expect.assertions(4);

    mockDate("2019-10-10T12:00:00");

    patchWithCleanup(session, {
        expiration_date: "2019-10-20 12:00:00",
        expiration_reason: "renewal",
        storeData: true, // used by subscription service to know whether mail is installed
        warning: "admin",
    });
    onRpc("get_param", ({ args }) => {
        expect.step("get_param");
        expect(args[0]).toBe("database.expiration_date");
        return "2019-10-24 12:00:00";
    });
    onRpc("update_notification", () => {
        expect.step("update_notification");
        return true;
    });
    await mountWithCleanup(WebClientEnterprise);
    await animationFrame();

    // click on "I paid, please recheck!"
    expect("a.check_enterprise_status").toHaveText("I paid, please recheck!");
    await click("a.check_enterprise_status");
    await animationFrame();

    expect(".oe_instance_register.oe_subscription_updated").toHaveText(
        "Your subscription was updated and is valid until October 24, 2019."
    );

    expect.verifySteps(["update_notification", "get_param"]);
});

// Why would we want to reload the page when we check the status and it hasn't changed?
test.skip("One app installed, check status and get page reload", async () => {
    expect.assertions(4);

    mockDate("2019-10-10T12:00:00");

    patchWithCleanup(session, {
        expiration_date: "2019-10-20 12:00:00",
        expiration_reason: "renewal",
        storeData: true, // used by subscription service to know whether mail is installed
        warning: "admin",
    });
    onRpc("get_param", () => {
        expect.step("get_param");
        return "2019-10-20 12:00:00";
    });
    onRpc("update_notification", () => {
        expect.step("update_notification");
        return true;
    });
    await mountWithCleanup(WebClientEnterprise);
    await animationFrame();

    // click on "I paid, please recheck!"
    await click("a.check_enterprise_status");
    await animationFrame();

    expect.verifySteps(["update_notification", "get_param", "reloadPage"]);
});

test("One app installed, upgrade database", async () => {
    expect.assertions(4);

    mockDate("2019-10-10T12:00:00");

    patchWithCleanup(session, {
        expiration_date: "2019-10-20 12:00:00",
        expiration_reason: "upsell",
        storeData: true, // used by subscription service to know whether mail is installed
        warning: "admin",
    });
    onRpc("get_param", ({ args }) => {
        expect.step("get_param");
        expect(args[0]).toBe("database.enterprise_code");
        return "ABC";
    });
    onRpc("search_count", () => {
        expect.step("search_count");
        return 13;
    });
    onRpc("update_notification", () => true);
    await mountWithCleanup(WebClientEnterprise);
    await animationFrame();
    await runAllTimers();

    expect(".oe_instance_register").toHaveText(
        "This database will expire in 10 days. You have more users or more apps installed than your subscription allows.\n\n" +
            "Upgrade your subscription\n" +
            "I paid, please recheck!"
    );

    // click on "Upgrade your subscription"
    await click("a.oe_instance_upsell");
    await animationFrame();

    expect.verifySteps(["get_param", "search_count"]);
    expect(browser.location.href).toBe(
        "https://www.odoo.com/odoo-enterprise/upsell?num_users=13&contract=ABC"
    );
});

test("One app installed, message for non admin user", async () => {
    expect.assertions(2);

    mockDate("2019-10-10T12:00:00");

    patchWithCleanup(session, {
        expiration_date: "2019-11-08 12:00:00",
        expiration_reason: "",
        storeData: true, // used by subscription service to know whether mail is installed
        warning: "user",
    });
    await mountWithCleanup(WebClientEnterprise);
    await animationFrame();

    expect(".oe_instance_register").toHaveText(
        "This database will expire in 29 days. Log in as an administrator to correct the issue."
    );

    expect(".database_expiration_panel").toHaveClass("alert-info", {
        message: "Color should be grey",
    });
});

test("One app installed, navigation to renewal page", async () => {
    expect.assertions(8);

    mockDate("2019-11-10T00:00:00");

    patchWithCleanup(session, {
        expiration_date: "2019-10-20 12:00:00",
        expiration_reason: "renewal",
        storeData: true, // used by subscription service to know whether mail is installed
        warning: "admin",
    });
    onRpc("get_param", ({ args }) => {
        expect.step("get_param");
        expect(args[0]).toBe("database.enterprise_code");
        return "ABC";
    });
    onRpc("update_notification", () => {
        expect.step("update_notification");
        return true;
    });
    await mountWithCleanup(WebClientEnterprise);
    await animationFrame();
    await runAllTimers();

    expect(".oe_instance_register").toHaveText(
        "This database has expired.\nRenew now\nI paid, please recheck!"
    );

    expect(".database_expiration_panel").toHaveClass("alert-danger");
    expect(".oe_instance_renew").toHaveCount(1, { message: "Part 'Register your subscription'" });
    expect("a.check_enterprise_status").toHaveCount(1, {
        message: "there should be a button for status checking",
    });

    expect(".oe_instance_register_form").toHaveCount(0);

    // Click on 'Renew your subscription'
    await click(".oe_instance_renew");
    await animationFrame();

    expect(browser.location.href).toBe("https://www.odoo.com/odoo-enterprise/renew?contract=ABC");

    expect.verifySteps(["get_param"]);
});

test("One app installed, different locale (arabic)", async () => {
    expect.assertions(1);

    mockDate("2019-25-09T12:00:00");

    patchWithCleanup(session, {
        expiration_date: "2019-10-20 12:00:00",
        expiration_reason: "renewal",
        storeData: true, // used by subscription service to know whether mail is installed
        warning: "admin",
    });
    serverState.lang = "ar-001";
    onRpc("get_param", () => "2019-11-09 12:00:00");
    onRpc("update_notification", () => true);
    await mountWithCleanup(WebClientEnterprise);
    await animationFrame();

    await click("a.check_enterprise_status");
    await animationFrame();

    expect(".oe_instance_register").toHaveText(
        "Your subscription was updated and is valid until ٩ نوفمبر ٢٠١٩."
    );
});
