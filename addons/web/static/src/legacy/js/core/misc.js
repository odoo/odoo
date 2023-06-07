/** @odoo-module alias=web.framework **/

import { _t } from "@web/core/l10n/translation";
import ajax from "web.ajax";
import Widget from "web.Widget";

var messages_by_seconds = function() {
    return [
        [0, _t("Loading...")],
        [20, _t("Still loading...")],
        [60, _t("Still loading...<br />Please be patient.")],
        [120, _t("Don't leave yet,<br />it's still loading...")],
        [300, _t("You may not believe it,<br />but the application is actually loading...")],
        [420, _t("Take a minute to get a coffee,<br />because it's loading...")],
        [3600, _t("Maybe you should consider reloading the application by pressing F5...")]
    ];
};

var Throbber = Widget.extend({
    template: "Throbber",
    start: function() {
        this.start_time = new Date().getTime();
        this.act_message();
    },
    act_message: function() {
        var self = this;
        setTimeout(function() {
            if (self.isDestroyed())
                return;
            var seconds = (new Date().getTime() - self.start_time) / 1000;
            var mes;
            messages_by_seconds().forEach((el) => {
                if (seconds >= el[0])
                    mes = el[1];
            });
            self.$(".oe_throbber_message").html(mes);
            self.act_message();
        }, 1000);
    },
});

/** Setup blockui */
if ($.blockUI) {
    $.blockUI.defaults.baseZ = 1100;
    $.blockUI.defaults.message = '<div class="openerp oe_blockui_spin_container" style="background-color: transparent;">';
    $.blockUI.defaults.css.border = '0';
    $.blockUI.defaults.css["background-color"] = '';
}


/**
 * Remove the "accesskey" attributes to avoid the use of the access keys
 * while the blockUI is enable.
 */

function blockAccessKeys() {
    var elementWithAccessKey = [];
    elementWithAccessKey = document.querySelectorAll('[accesskey]');
    elementWithAccessKey.forEach((elem) => {
        elem.setAttribute("data-accesskey",elem.getAttribute('accesskey'));
        elem.removeAttribute('accesskey');
    });
}

function unblockAccessKeys() {
    var elementWithDataAccessKey = [];
    elementWithDataAccessKey = document.querySelectorAll('[data-accesskey]');
    elementWithDataAccessKey.forEach((elem) => {
        elem.setAttribute('accesskey', elem.getAttribute('data-accesskey'));
        elem.removeAttribute('data-accesskey');
    });
}

var throbbers = [];

function blockUI() {
    var tmp = $.blockUI.apply($, arguments);
    var throbber = new Throbber();
    throbbers.push(throbber);
    throbber.appendTo($(".oe_blockui_spin_container"));
    $(document.body).addClass('o_ui_blocked');
    blockAccessKeys();
    return tmp;
}

function unblockUI() {
    throbbers.forEach((throbber) => {
        throbber.destroy();
    });
    throbbers = [];
    $(document.body).removeClass('o_ui_blocked');
    unblockAccessKeys();
    return $.unblockUI.apply($, arguments);
}

/**
 * Redirect to url by replacing window.location
 * If wait is true, sleep 1s and wait for the server i.e. after a restart.
 */
function redirect (url, wait) {
    var load = function() {
        var old = "" + window.location;
        var old_no_hash = old.split("#")[0];
        var url_no_hash = url.split("#")[0];
        location.assign(url);
        if (old_no_hash === url_no_hash) {
            location.reload(true);
        }
    };

    var wait_server = function() {
        ajax.rpc("/web/webclient/version_info", {}).then(load).guardedCatch(function () {
            setTimeout(wait_server, 250);
        });
    };

    if (wait) {
        setTimeout(wait_server, 1000);
    } else {
        load();
    }
}


// In Internet Explorer, document doesn't have the contains method, so we make a
// polyfill for the method in order to be compatible.
if (!document.contains) {
    document.contains = function contains (node) {
        if (!(0 in arguments)) {
            throw new TypeError('1 argument is required');
        }

        do {
            if (this === node) {
                return true;
            }
        } while (node = node && node.parentNode);

        return false;
    };
}

export default {
    blockUI: blockUI,
    unblockUI: unblockUI,
    redirect: redirect,
};
