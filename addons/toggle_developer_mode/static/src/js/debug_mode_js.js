/** @odoo-module **/

import { UserMenu } from "@web/webclient/user_menu/user_menu";
import { routeToUrl } from "@web/core/browser/router_service";
import { patch } from "@web/core/utils/patch";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
const userMenuRegistry = registry.category("user_menuitems");

patch(UserMenu.prototype, "toggle_developer_mode.UserMenu", {
    setup() {
        this._super.apply(this, arguments);
        userMenuRegistry.remove("documentation");
        userMenuRegistry.remove("support");
        userMenuRegistry.remove("odoo_account");
        userMenuRegistry.add("debug", debugItem)
//             .add("leave_debug", leaveDebugMode)
            .add("separator0", separator8)
            .add("documentation", documentationItem)
            .add("support", supportItem)
    },
    // getElements() {
    //     var ret = this._super.apply(this, arguments);
    //     return ret;
    // },
});

function debugItem(env) {
    const url_debug = $.param.querystring(window.location.href, 'debug=1');
    if (window.location.href.indexOf('debug=1') > -1){
         return {
            type: "item",
            description:env._t("Deactivate the developer mode"),
            callback: () => {
                const route = env.services.router.current;
                route.search.debug = "";
                browser.location.href = browser.location.origin + routeToUrl(route);
            },
            sequence: 7,
        };
     }
    else {
        return {
            type: "item",
            id: "debug",
            description:''.concat(env._t("Activate the developer mode")),
            href: url_debug,
            callback: () => {
                browser.open(url_debug, "_self");
            },
            sequence: 5,
        };
    //otherwise
    }
}

// function activateAssetsDebugging(env) {
//     return {
//         type: "item",
//         description: env._t("Activate Assets Debugging"),
//         callback: () => {
//             browser.location.search = "?debug=assets";
//         },
//         sequence: 6,
//     };
// }

// function leaveDebugMode(env) {
//     return {
//         type: "item",
//         description: env._t("Dectivate the developer mode"),
//         callback: () => {
//             const route = env.services.router.current;
//             route.search.debug = "";
//             browser.location.href = browser.location.origin + routeToUrl(route);
//         },
//         sequence: 7,
//     };
// }

function separator8() {
    return {
        type: "separator",
        sequence: 8,
    };
}
function documentationItem(env) {
    const documentationURL = "https://www.odoo.com/documentation/15.0";
    return {
        type: "item",
        id: "documentation",
        description: env._t("Documentation"),
        href: documentationURL,
        callback: () => {
            browser.open(documentationURL, "_blank");
        },
        sequence: 10,
    };
}

function supportItem(env) {
    const url = session.support_url;
    return {
        type: "item",
        id: "support",
        description: env._t("Support"),
        href: url,
        callback: () => {
            browser.open(url, "_blank");
        },
        sequence: 20,
    };
}

// function odooAccountItem(env) {
//     const app_account_title = session.app_account_title;
//     const app_account_url = session.app_account_url;
//     return {
//         type: "item",
//         id: "account",
//         description: env._t(app_account_title),
//         href: app_account_url,
//         callback: () => {
//             browser.open(app_account_url, "_blank");
//         },
//         sequence: 60,
//     };
// }

// odoo.define('toggle_developer_mode.DebugModeJs', function (require) {
//     "use strict";

// var DebugModeJs = require('web.UserMenu');

// DebugModeJs.include({
//     start: function () {
//         var self = this;
//         return this._super.apply(this, arguments).then(function () {
//             var mMode = 'normal';
//             if (window.location.href.indexOf('debug=1') > -1)
//                 mMode = 'debug';
//             if (mMode == 'normal')
//                 self.$('[data-menu="quitdebug"]').hide();
//             if (mMode == 'debug')
//                 self.$('[data-menu="debug"]').hide();
//         });
//     },

//     _onMenuDebug: function () {
//         window.location = $.param.querystring(window.location.href, 'debug=1');
//     },
//     _onMenuQuitdebug: function () {
//         window.location = $.param.querystring(window.location.href, 'debug=0');
//     },
// })

// });
