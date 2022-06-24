odoo.define('web.framework', function (require) {
"use strict";

var core = require('web.core');
var ajax = require('web.ajax');
var Widget = require('web.Widget');
const {sprintf} = require('web.utils')

var _t = core._t;

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
            _.each(messages_by_seconds(), function(el) {
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
    _.each(elementWithAccessKey, function (elem) {
        elem.setAttribute("data-accesskey",elem.getAttribute('accesskey'));
        elem.removeAttribute('accesskey');
    });
}

function unblockAccessKeys() {
    var elementWithDataAccessKey = [];
    elementWithDataAccessKey = document.querySelectorAll('[data-accesskey]');
    _.each(elementWithDataAccessKey, function (elem) {
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
    _.invoke(throbbers, 'destroy');
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

//  * Client action to reload the whole interface.
//  * If params.menu_id, it opens the given menu entry.
//  * If params.wait, reload will wait the openerp server to be reachable before reloading

function Reload(parent, action) {
    var params = action.params || {};
    var menu_id = params.menu_id || false;
    var action_id = params.action_id || false;
    var l = window.location;

    var sobj = $.deparam(l.search.substr(1));
    if (params.url_search) {
        sobj = _.extend(sobj, params.url_search);
    }
    var search = '?' + $.param(sobj);

    var hash = l.hash;
    if (menu_id) {
        hash = "#menu_id=" + menu_id;
        if (action_id) {
            hash += "&action=" + action_id;
        }
    } else if (action_id) {
        hash = "#action=" + action_id;
    }
    var url = l.protocol + "//" + l.host + l.pathname + search + hash;

    // Clear cache
    core.bus.trigger('clear_cache');

    redirect(url, params.wait);
}

core.action_registry.add("reload", Reload);


/**
 * Client action to go back home.
 */
function Home (parent, action) {
    var url = '/' + (window.location.search || '');
    redirect(url, action && action.params && action.params.wait);
}
core.action_registry.add("home", Home);

function login() {
    redirect('/web/login');
}
core.action_registry.add("login", login);

function logout() {
    redirect('/web/session/logout');
}
core.action_registry.add("logout", logout);

/**
 * @param {ActionManager} parent
 * @param {Object} action
 * @param {Object} action.params notification params
 * @see ServiceMixin.displayNotification
 */
function displayNotification(parent, action) {
    let {title='', message='', links=[], type='info', sticky=false, next} = action.params || {};
    links = links.map(({url, label}) => `<a href="${_.escape(url)}" target="_blank">${_.escape(label)}</a>`)
    parent.displayNotification({
        title, // no escape for the title because it is done in the template
        message: owl.markup(sprintf(_.escape(message), ...links)),
        type,
        sticky,
    });
    return next;
}
core.action_registry.add("display_notification", displayNotification);

/**
 * Client action to refresh the session context (making sure
 * HTTP requests will have the right one) then reload the
 * whole interface.
 */
function ReloadContext (parent, action) {
    // side-effect of get_session_info is to refresh the session context
    ajax.rpc("/web/session/get_session_info", {}).then(function() {
        Reload(parent, action);
    });
}
core.action_registry.add("reload_context", ReloadContext);

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

return {
    blockUI: blockUI,
    unblockUI: unblockUI,
    redirect: redirect,
};

});
