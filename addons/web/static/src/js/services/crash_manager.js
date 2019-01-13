odoo.define('web.CrashManager', function (require) {
"use strict";

var ajax = require('web.ajax');
var core = require('web.core');
var Dialog = require('web.Dialog');

var QWeb = core.qweb;
var _t = core._t;
var _lt = core._lt;

var map_title ={
    user_error: _lt('Warning'),
    warning: _lt('Warning'),
    access_error: _lt('Access Error'),
    missing_error: _lt('Missing Record'),
    validation_error: _lt('Validation Error'),
    except_orm: _lt('Global Business Error'),
    access_denied: _lt('Access Denied'),
};

var CrashManager = core.Class.extend({
    init: function() {
        this.active = true;
    },
    enable: function () {
        this.active = true;
    },
    disable: function () {
        this.active = false;
    },
    rpc_error: function(error) {
        var self = this;
        if (!this.active) {
            return;
        }
        if (this.connection_lost) {
            return;
        }
        if (error.code === -32098) {
            core.bus.trigger('connection_lost');
            this.connection_lost = true;
            var timeinterval = setInterval(function() {
                var options = {shadow: true};
                ajax.jsonRpc('/web/webclient/version_info', 'call', {}, options).then(function () {
                    clearInterval(timeinterval);
                    core.bus.trigger('connection_restored');
                    self.connection_lost = false;
                });
            }, 2000);
            return;
        }
        var handler = core.crash_registry.get(error.data.name, true);
        if (handler) {
            new (handler)(this, error).display();
            return;
        }
        if (_.has(map_title, error.data.exception_type)) {
            if(error.data.exception_type === 'except_orm'){
                if(error.data.arguments[1]) {
                    error = _.extend({}, error,
                                {
                                    data: _.extend({}, error.data,
                                        {
                                            message: error.data.arguments[1],
                                            title: error.data.arguments[0] !== 'Warning' ? (" - " + error.data.arguments[0]) : '',
                                        })
                                });
                }
                else {
                    error = _.extend({}, error,
                                {
                                    data: _.extend({}, error.data,
                                        {
                                            message: error.data.arguments[0],
                                            title:  '',
                                        })
                                });
                }
            }
            else {
                error = _.extend({}, error,
                            {
                                data: _.extend({}, error.data,
                                    {
                                        message: error.data.arguments[0],
                                        title: map_title[error.data.exception_type] !== 'Warning' ? (" - " + map_title[error.data.exception_type]) : '',
                                    })
                            });
            }

            this.show_warning(error);
        //InternalError

        } else {
            this.show_error(error);
        }
    },
    show_warning: function(error) {
        if (!this.active) {
            return;
        }
        return new Dialog(this, {
            size: 'medium',
            title: _.str.capitalize(error.type || error.message) || _t("Odoo Warning"),
            subtitle: error.data.title,
            $content: $(QWeb.render('CrashManager.warning', {error: error}))
        }).open({shouldFocusButtons:true});
    },
    show_error: function(error) {
        if (!this.active) {
            return;
        }
        var dialog = new Dialog(this, {
            title: _.str.capitalize(error.type || error.message) || _t("Odoo Error"),
            $content: $(QWeb.render('CrashManager.error', {error: error}))
        });

        // When the dialog opens, initialize the copy feature and destroy it when the dialog is closed
        var $clipboardBtn;
        var clipboard;
        dialog.opened(function () {
            // When the full traceback is shown, scroll it to the end (useful for better python error reporting)
            dialog.$(".o_error_detail").on("shown.bs.collapse", function (e) {
                e.target.scrollTop = e.target.scrollHeight;
            });

            $clipboardBtn = dialog.$(".o_clipboard_button");
            $clipboardBtn.tooltip({title: _t("Copied !"), trigger: "manual", placement: "left"});
            clipboard = new window.ClipboardJS($clipboardBtn[0], {
                text: function () {
                    return (_t("Error") + ":\n" + error.message + "\n\n" + error.data.debug).trim();
                },
                // Container added because of Bootstrap modal that give the focus to another element.
                // We need to give to correct focus to ClipboardJS (see in ClipboardJS doc)
                // https://github.com/zenorocha/clipboard.js/issues/155
                container: dialog.el,
            });
            clipboard.on("success", function (e) {
                _.defer(function () {
                    $clipboardBtn.tooltip("show");
                    _.delay(function () {
                        $clipboardBtn.tooltip("hide");
                    }, 800);
                });
            });
        });
        dialog.on("closed", this, function () {
            $clipboardBtn.tooltip('dispose');
            clipboard.destroy();
        });

        return dialog.open();
    },
    show_message: function(exception) {
        return this.show_error({
            type: _t("Odoo Client Error"),
            message: exception,
            data: {debug: ""}
        });
    },
});

/**
 * An interface to implement to handle exceptions. Register implementation in instance.web.crash_manager_registry.
*/
var ExceptionHandler = {
    /**
     * @param parent The parent.
     * @param error The error object as returned by the JSON-RPC implementation.
     */
    init: function(parent, error) {},
    /**
     * Called to inform to display the widget, if necessary. A typical way would be to implement
     * this interface in a class extending instance.web.Dialog and simply display the dialog in this
     * method.
     */
    display: function() {},
};


/**
 * Handle redirection warnings, which behave more or less like a regular
 * warning, with an additional redirection button.
 */
var RedirectWarningHandler = Dialog.extend(ExceptionHandler, {
    init: function(parent, error) {
        this._super(parent);
        this.error = error;
    },
    display: function() {
        var self = this;
        var error = this.error;
        error.data.message = error.data.arguments[0];

        new Dialog(this, {
            size: 'medium',
            title: _.str.capitalize(error.type) || _t("Odoo Warning"),
            buttons: [
                {text: error.data.arguments[2], classes : "btn-primary", click: function() {
                    window.location.href = '#action='+error.data.arguments[1];
                    self.destroy();
                }},
                {text: _t("Cancel"), click: function() { self.destroy(); }, close: true}
            ],
            $content: QWeb.render('CrashManager.warning', {error: error}),
        }).open();
    }
});

core.crash_registry.add('odoo.exceptions.RedirectWarning', RedirectWarningHandler);

function session_expired(cm) {
    return {
        display: function () {
            cm.show_warning({type: _t("Odoo Session Expired"), data: {message: _t("Your Odoo session expired. Please refresh the current web page.")}});
        }
    }
}
core.crash_registry.add('odoo.http.SessionExpiredException', session_expired);
core.crash_registry.add('werkzeug.exceptions.Forbidden', session_expired);

core.crash_registry.add('504', function (cm) {
    return {
        display: function () {
            cm.show_warning({
                type: _t("Request timeout"),
                data: {message: _t("The operation was interrupted. This usually means that the current operation is taking too much time.")}});
        }
    }
});

return CrashManager;
});

odoo.define('web.crash_manager', function (require) {
"use strict";

var CrashManager = require('web.CrashManager');
return new CrashManager();

});
