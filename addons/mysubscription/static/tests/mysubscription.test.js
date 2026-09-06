import { expect, test } from "@odoo/hoot";
import {
    contains,
    defineMenus,
    mockService,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { user } from "@web/core/user";

import { MySubscriptionDashboard } from "@mysubscription/dashboard";
import { MySubscriptionNavBar } from "@mysubscription/components/navbar";

/**
 * @param {Object} [options]
 * @param {string|false} [options.enterpriseCode]
 * @param {string|false} [options.expirationDate]
 */
function mockDashboardData({ enterpriseCode = "123-456-789", expirationDate = "2999-01-01" } = {}) {
    // Required by DatabaseSection's onWillStart.
    patchWithCleanup(user, { hasGroup: () => Promise.resolve(false) });
    onRpc("/web/database/list", () => ["test_db"]);
    onRpc("mysubscription.mysubscription", "get_iap_data", () => []);
    onRpc("mysubscription.mysubscription", "get_dashboard_data", () => ({
        enterprise_code: enterpriseCode,
        base_url: "http://localhost:8069",
        expiration_reason: false,
        expiration_date: expirationDate,
    }));
}

test("active subscription: Enterprise plan is current and the upgrade link targets the on-premise flow", async () => {
    mockEnterprise();
    mockDashboardData({ enterpriseCode: "123-456-789", expirationDate: "2999-01-01" });
    await mountWithCleanup(MySubscriptionDashboard);

    expect(".card:eq(0)").not.toHaveClass("border-primary", { message: "Community plan is not current" });
    expect(".card:eq(1)").toHaveClass("border-primary", { message: "Enterprise plan is current" });
    expect(".card:eq(1) a:contains('My Account')").toHaveCount(1);
    expect(".card:eq(1) button:contains('Subscription')").toHaveCount(1);
    expect("a:contains('Upgrade')").toHaveAttribute("href", "https://upgrade.odoo.com/#onpremise");
});

test("active subscription without the Enterprise webclient: falls back to the Switch button", async () => {
    mockDashboardData({ enterpriseCode: "123-456-789", expirationDate: "2999-01-01" });
    await mountWithCleanup(MySubscriptionDashboard);

    expect(".card:eq(1)").toHaveClass("border-primary", { message: "Enterprise plan is still current" });
    expect(".card:eq(1) a:contains('My Account')").toHaveCount(0);
    expect(".card:eq(1) button:contains('Subscription')").toHaveCount(0);
    expect(".card:eq(1) a:contains('Switch')").toHaveCount(1);
});

test("no subscription: Community plan is current and the upgrade link targets the pricing page", async () => {
    mockDashboardData({ enterpriseCode: false, expirationDate: false });
    await mountWithCleanup(MySubscriptionDashboard);

    expect(".card:eq(0)").toHaveClass("border-primary", { message: "Community plan is current" });
    expect(".card:eq(1)").not.toHaveClass("border-primary", { message: "Enterprise plan is not current" });
    expect(".card:eq(1) a:contains('Switch')").toHaveCount(1);
    expect("a:contains('Upgrade')").toHaveAttribute("href", "https://www.odoo.com/pricing");
});

test("expired subscription: behaves the same as having no subscription", async () => {
    mockDashboardData({ enterpriseCode: "123-456-789", expirationDate: "2000-01-01" });
    await mountWithCleanup(MySubscriptionDashboard);

    expect(".card:eq(0)").toHaveClass("border-primary", { message: "Community plan is current" });
    expect(".card:eq(1) a:contains('Switch')").toHaveCount(1);
});

function mountNavBar(props = {}) {
    return mountWithCleanup(MySubscriptionNavBar, {
        props: { hasSubscription: false, ...props },
    });
}

/**
 * The "home_menu" and "enterprise_subscription" services only exist when
 * web_enterprise is installed. Registering them here simulates running on
 * an Enterprise database.
 */
function mockEnterprise() {
    const toggleCalls = [];
    mockService("home_menu", () => ({
        hasHomeMenu: false,
        hasBackgroundAction: false,
        toggle(show) {
            toggleCalls.push(show);
        },
    }));
    mockService("enterprise_subscription", () => ({}));
    return toggleCalls;
}

test.tags("desktop");
test("community: shows the standard apps dropdown, with the app name once", async () => {
    defineMenus([{ id: 1, actionID: 1 }]);
    await mountNavBar();

    expect(".o_navbar_apps_menu button.dropdown-toggle").toHaveCount(1);
    expect("a.o_menu_toggle").toHaveCount(0);
    expect(".o_menu_brand").toHaveCount(1);
    expect(".o_menu_brand").toHaveText("My Subscription");

    await contains(".o_navbar_apps_menu button.dropdown-toggle").click();
    expect(".dropdown-menu").toHaveCount(1);
});

test.tags("desktop");
test("enterprise: replaces the dropdown with a home-menu link showing the app icon and name once", async () => {
    mockEnterprise();
    await mountNavBar();

    expect(".o_navbar_apps_menu").toHaveCount(0);
    expect("a.o_menu_toggle").toHaveCount(1);
    expect("a.o_menu_toggle").toHaveClass("hasImage");
    expect(".o_menu_brand_icon").toHaveAttribute("data-src", "/mysubscription/static/src/img/odoo_o.svg");
    expect(".o_menu_brand").toHaveCount(1);
    expect("a.o_menu_toggle .o_menu_brand").toHaveCount(1);
});

test.tags("desktop");
test("enterprise: clicking the apps icon opens the home menu instead of navigating away", async () => {
    const toggleCalls = mockEnterprise();
    await mountNavBar();

    await contains("a.o_menu_toggle").click();
    expect(toggleCalls).toEqual([true]);
});
