odoo.define('web.CrashManager', function (require) {
"use strict";

var ajax = require('web.ajax');
var core = require('web.core');
var Dialog = require('web.Dialog');
var mixins = require('web.mixins');
var ServicesMixin = require('web.ServicesMixin');
var ServiceProviderMixin = require('web.ServiceProviderMixin');
var Widget = require('web.Widget');

var _t = core._t;
var _lt = core._lt;

var map_title ={
    user_error: _lt("User Error"),
    warning: _lt("Warning"),
    access_error: _lt("Access Error"),
    missing_error: _lt("Missing Record"),
    validation_error: _lt("Validation Error"),
    except_orm: _lt("Global Business Error"),
    access_denied: _lt("Access Denied"),
    karma_error: _lt("Karma Error"),
};

/**
 * An extension of Dialog Widget to render the warnings and errors on the website.
 * Extend it with your template of choice like ErrorDialog/WarningDialog
 */
var CrashManagerDialog = Dialog.extend({
    xmlDependencies: (Dialog.prototype.xmlDependencies || []).concat(
        ['/web/static/src/xml/crash_manager.xml']
    ),

    /**
     * @param {Object} error
     * @param {string} error.message    the message in Warning/Error Dialog
     * @param {string} error.traceback  the traceback in ErrorDialog
     *
     * @constructor
     */
    init: function (parent, options, error) {
        this._super.apply(this, [parent, options]);
        this.message = error.message;
        this.traceback = error.traceback;
    },
});

var ErrorDialog = CrashManagerDialog.extend({
    template: 'CrashManager.error',
});

var WarningDialog = CrashManagerDialog.extend({
    template: 'CrashManager.warning',

    /**
     * Sets size to medium by default.
     *
     * @override
     */
    init: function (parent, options, error) {
        this._super(parent, _.extend({
            size: 'medium',
       }, options), error);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Focuses the ok button.
     *
     * @override
     */
    open: function () {
        this._super({shouldFocusButtons: true});
    },
});

var CrashManager = core.Class.extend(mixins.EventDispatcherMixin, ServicesMixin, ServiceProviderMixin,{
    init: function () {
        var self = this;
        this.active = true;
        this.isConnected = true;

        mixins.EventDispatcherMixin.init.call(this);

        // crash manager integration
        core.bus.on('rpc_error', this, this.rpc_error);
        window.onerror = function (message, file, line, col, error) {
            // Scripts injected in DOM (eg: google API's js files) won't return a clean error on window.onerror.
            // The browser will just give you a 'Script error.' as message and nothing else for security issue.
            // To enable onerror to work properly with CORS file, you should:
            //   1. add crossorigin="anonymous" to your <script> tag loading the file
            //   2. enabling 'Access-Control-Allow-Origin' on the server serving the file.
            // Since in some case it wont be possible to to this, this handle should have the possibility to be
            // handled by the script manipulating the injected file. For this, you will use window.onOriginError
            // If it is not handled, we should display something clearer than the common crash_manager error dialog
            // since it won't show anything except "Script error."
            // This link will probably explain it better: https://blog.sentry.io/2016/05/17/what-is-script-error.html
            if (!file && !line && !col) {
                // Chrome and Opera set "Script error." on the `message` and hide the `error`
                // Firefox handles the "Script error." directly. It sets the error thrown by the CORS file into `error`
                if (window.onOriginError) {
                    window.onOriginError();
                    delete window.onOriginError;
                } else {
                    self.show_error({
                        type: _t("Odoo Client Error"),
                        message: _t("Unknown CORS error"),
                        data: {debug: _t("An unknown CORS error occured. The error probably originates from a JavaScript file served from a different origin. (Opening your browser console might give you a hint on the error.)")},
                    });
                }
            } else {
                // ignore Chrome video internal error: https://crbug.com/809574
                if (!error && message === 'ResizeObserver loop limit exceeded') {
                    return;
                }
                var traceback = error ? error.stack : '';
                self.show_error({
                    type: _t("Odoo Client Error"),
                    message: message,
                    data: {debug: file + ':' + line + "\n" + _t('Traceback:') + "\n" + traceback},
                });
            }
        };

        // listen to unhandled rejected promises, and throw an error when the
        // promise has been rejected due to a crash
        window.addEventListener('unhandledrejection', function (ev) {
            if (ev.reason && ev.reason instanceof Error) {
                var traceback = ev.reason.stack;
                self.show_error({
                    type: _t("Odoo Client Error"),
                    message: '',
                    data: {debug: _t('Traceback:') + "\n" + traceback},
                });
            } else {
                // the rejection is not due to an Error, so prevent the browser
                // from displaying an 'unhandledrejection' error in the console
                ev.stopPropagation();
                ev.stopImmediatePropagation();
                ev.preventDefault();
            }
        });
        ServiceProviderMixin.init.call(this);
    },
    enable: function () {
        this.active = true;
    },
    disable: function () {
        this.active = false;
    },
    handleLostConnection: function () {
        var self = this;
        if (!this.isConnected) {
            // already handled, nothing to do.  This can happen when several
            // rpcs are done in parallel and fail because of a lost connection.
            return;
        }
        this.isConnected = false;
        var delay = 2000;
        core.bus.trigger('connection_lost');

        setTimeout(function checkConnection() {
            ajax.jsonRpc('/web/webclient/version_info', 'call', {}, {shadow:true}).then(function () {
                core.bus.trigger('connection_restored');
                self.isConnected = true;
            }).guardedCatch(function () {
                // exponential backoff, with some jitter
                delay = (delay * 1.5) + 500*Math.random();
                setTimeout(checkConnection, delay);
            });
        }, delay);
    },
    rpc_error: function(error) {
        if (!this.active) {
            return;
        }
        if (this.connection_lost) {
            return;
        }
        if (error.code === -32098) {
            this.handleLostConnection();
            return;
        }
        var handler = core.crash_registry.get(error.data.name, true);
        if (handler) {
            new (handler)(this, error).display();
            return;
        }
        if (_.has(map_title, error.data.exception_type)) {
            if (error.data.exception_type === 'except_orm') {
                if (error.data.arguments[1]) {
                    error = _.extend({}, error,
                                {
                                    data: _.extend({}, error.data,
                                        {
                                            message: error.data.arguments[1],
                                            title: error.data.arguments[0] !== 'Warning' ? error.data.arguments[0] : '',
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
                                        title: map_title[error.data.exception_type] !== 'Warning' ? map_title[error.data.exception_type] : '',
                                    })
                            });
            }
            this.show_warning(error);
        } else {
            this.show_error(error);
        }
    },
    show_warning: function (error, options) {
        if (!this.active) {
            return;
        }
        var message = error.data ? error.data.message : error.message;
        var title = _.str.capitalize(error.type) || _t("Oops Something went wrong !");
        var subtitle = error.data ? error.data.title : error.title;
        this.displayNotification(_.extend({
            title: title,
            message: message,
            subtitle: subtitle,
            sticky: true,
        }, options));
    },
    show_error: function (error) {
        if (!this.active) {
            return;
        }
        var dialog = new ErrorDialog(this, {
            title: _.str.capitalize(error.type) || _t("Odoo Error"),
        }, {
            message: error.message,
            traceback: error.data.debug,
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
var RedirectWarningHandler = Widget.extend(ExceptionHandler, {
    init: function(parent, error) {
        this._super(parent);
        this.error = error;
    },
    display: function() {
        var self = this;
        var error = this.error;

        new WarningDialog(this, {
            title: _.str.capitalize(error.type) || _t("Odoo Warning"),
            buttons: [
                {text: error.data.arguments[2], classes : "btn-primary", click: function() {
                    $.bbq.pushState({
                        'action': error.data.arguments[1],
                        'cids': $.bbq.getState().cids,
                    }, 2);
                    self.destroy();
                    location.reload();
                }},
                {text: _t("Cancel"), click: function() { self.destroy(); }, close: true}
            ]
        }, {
            message: error.data.arguments[0],
        }).open();
    }
});

core.crash_registry.add('odoo.exceptions.RedirectWarning', RedirectWarningHandler);

function session_expired(cm) {
    return {
        display: function () {
            cm.show_warning({type: _t("Odoo Session Expired"), message: _t("Your Odoo session expired. Please refresh the current web page.")});
        }
    };
}
core.crash_registry.add('odoo.http.SessionExpiredException', session_expired);
core.crash_registry.add('werkzeug.exceptions.Forbidden', session_expired);

core.crash_registry.add('504', function (cm) {
    return {
        display: function () {
            cm.show_warning({
                type: _t("Request timeout"),
                message: _t("The operation was interrupted. This usually means that the current operation is taking too much time.")});
        }
    };
});

return {
    CrashManager: CrashManager,
    ErrorDialog: ErrorDialog,
    WarningDialog: WarningDialog,
};
});

odoo.define('web.crash_manager', function (require) {
"use strict";

var CrashManager = require('web.CrashManager').CrashManager;
return new CrashManager();

});
