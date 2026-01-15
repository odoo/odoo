import { registry } from "@web/core/registry";
import { WORKER_STATE } from "@bus/workers/websocket_worker";
import { whenReady } from "@odoo/owl";

function logout() {
    return [
        {
            trigger: ".o_web_client .o_navbar",
            async run() {
                await whenReady();
                await new Promise((resolve) => requestAnimationFrame(resolve));
                await new Promise((resolve) => {
                    const bus = odoo.__WOWL_DEBUG__.root.env.services.bus_service;
                    bus.addEventListener("BUS:CONNECT", resolve, { once: true });
                    if (bus.workerState === WORKER_STATE.CONNECTED) {
                        resolve();
                    }
                });
            },
        },
        {
            content: "check we're logged in",
            trigger: ".o_user_menu .dropdown-toggle",
            run: "click",
        },
        {
            content: "click the Log out button",
            trigger: ".dropdown-item[data-menu=logout]",
            run: "click",
            expectUnloadPage: true,
        },
        {
            // Wait and check we are logged out
            // o_database_list is used in the case website is not installed and only portal is.
            trigger: ".oe_website_login_container, .o_database_list",
        },
    ];
}

registry.category("web_tour.tours").add("test_user_switch", {
    url: "/odoo",
    steps: () => [
        ...logout(),
        {
            content: "check if the login input is empty",
            trigger: "input#login:empty",
        },
        {
            content: "check if the password input is empty",
            trigger: "input#password:empty",
        },
        {
            content: "Should contains the user switch button",
            trigger: ".oe_login_form .o_user_switch_btn",
            run: "click",
        },
        {
            content: "Click on Marc Demo on the quick login page",
            trigger:
                ".o_user_switch:not(:has(.list-group-item:nth-child(2))) .list-group-item:contains('Marc Demo')",
            run: "click",
        },
        {
            content: "Check user choice button to back on the quick login page",
            trigger: ".oe_login_form .o_user_switch_btn",
            run: "click",
        },
        {
            content: "Display the login form",
            trigger: ".o_user_switch .fa-user-circle-o",
            run: "click",
        },
        {
            content: "fill the login",
            trigger: "input#login",
            run: "edit admin",
        },
        {
            content: "fill the password",
            trigger: "input#password",
            run: "edit admin",
        },
        {
            content: "click on login button",
            trigger: 'button:contains("Log in")',
            run: "click",
            expectUnloadPage: true,
        },
        ...logout(),
        {
            content: "Check if there is Mitchell Admin in user list selection",
            trigger: ".o_user_switch .list-group-item:nth-child(1):contains('Mitchell Admin')",
        },
        {
            content: "Check if there is Marc Demo in user list selection",
            trigger: ".o_user_switch .list-group-item:nth-child(2):contains('Marc Demo')",
        },
        {
            content: "Choice demo",
            trigger: ".o_user_switch .list-group-item:contains('Marc Demo')",
            run: "click",
        },
        {
            content: "check the login for demo",
            trigger: "input#login:value('demo')",
        },
        {
            content: "fill the password",
            trigger: "input#password",
            run: "edit demo",
        },
        {
            content: "Check back button to back on the quick login page",
            trigger: ".oe_login_form .o_user_switch_btn",
            run: "click",
        },
        {
            content: "Check have 2 users",
            trigger: ".o_user_switch .list-group-item:nth-child(2)",
        },
        {
            content: "Click on Mitchell Admin",
            trigger: ".o_user_switch .list-group-item:nth-child(1):contains('Mitchell Admin')",
            run: "click",
        },
        {
            content: "check the login for admin",
            trigger: "input#login:value('admin')",
        },
        {
            content: "fill the password",
            trigger: "input#password",
            run: "edit admin",
        },
        {
            content: "Check back button to back on the quick login page",
            trigger: ".oe_login_form .o_user_switch_btn",
            run: "click",
        },
        {
            content: "Display the login form",
            trigger: ".o_user_switch .fa-user-circle-o",
            run: "click",
        },
        {
            content: "the login form is display",
            trigger: "form.oe_login_form:not(.d-none)",
        },
        {
            content: "check if the login input is empty",
            trigger: "input#login:empty",
        },
        {
            content: "check if the password input is empty",
            trigger: "input#password:empty",
        },
        {
            content: "Back to user switch",
            trigger: ".oe_login_form .o_user_switch_btn",
            run: "click",
        },
        {
            content: "Remove the admin user from page",
            trigger: ".o_user_switch .d-flex:first-child .fa-times",
            run: "click",
        },
        {
            content: "only one user is left on quick login",
            trigger:
                ".o_user_switch:not(:has(.list-group-item:nth-child(2))) .list-group-item:contains('Marc Demo')",
        },
    ],
});
