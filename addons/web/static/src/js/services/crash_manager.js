odoo.define('web.ErrorDialogRegistry', function (require) {
"use strict";

var Registry = require('web.Registry');

return new Registry();
});

odoo.define('web.CrashManager', function (require) {
"use strict";

const AbstractService = require('web.AbstractService');
var ajax = require('web.ajax');
const BrowserDetection = require('web.BrowserDetection');
var core = require('web.core');
var Dialog = require('web.Dialog');
var ErrorDialogRegistry = require('web.ErrorDialogRegistry');
var Widget = require('web.Widget');

var _t = core._t;
var _lt = core._lt;

// Register this eventlistener before qunit does.
// Some errors needs to be negated by the crash_manager.
window.addEventListener('unhandledrejection', ev =>
    core.bus.trigger('crash_manager_unhandledrejection', ev)
);

let active = true;

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
        core.bus.off('close_dialogs', this);
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

var CrashManager = AbstractService.extend({
    init: function () {
        var self = this;
        active = true;
        this.isConnected = true;
        this.odooExceptionTitleMap = {
            'odoo.addons.base.models.ir_mail_server.MailDeliveryException': _lt("MailDeliveryException"),
            'odoo.exceptions.AccessDenied': _lt("Access Denied"),
            'odoo.exceptions.AccessError': _lt("Access Error"),
            'odoo.exceptions.MissingError': _lt("Missing Record"),
            'odoo.exceptions.UserError': _lt("User Error"),
            'odoo.exceptions.ValidationError': _lt("Validation Error"),
            'odoo.exceptions.Warning': _lt("Warning"),
        };

        this.browserDetection = new BrowserDetection();
        this._super.apply(this, arguments);

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
        core.bus.on('crash_manager_unhandledrejection', this, function (ev) {
            if (ev.reason && ev.reason instanceof Error) {
                // Error.prototype.stack is non-standard.
                // https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Error
                // However, most engines provide an implementation.
                // In particular, Chrome formats the contents of Error.stack
                // https://v8.dev/docs/stack-trace-api#compatibility
                let traceback;
                if (self.browserDetection.isBrowserChrome()) {
                    traceback = ev.reason.stack;
                } else {
                    traceback = `${_t("Error:")} ${ev.reason.message}\n${ev.reason.stack}`;
                }
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
    },
    enable: function () {
        active = true;
    },
    disable: function () {
        active = false;
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
        // Some qunit tests produces errors before the DOM is set.
        // This produces an error loop as the modal/toast has no DOM to attach to.
        if (!document.body || !active || this.connection_lost) return;

        // Connection lost error
        if (error.code === -32098) {
            this.handleLostConnection();
            return;
        }

        // Special exception handlers, see crash_registry bellow
        var handler = core.crash_registry.get(error.data.name, true);
        if (handler) {
            new (handler)(this, error).display();
            return;
        }

        // Odoo custom exception: UserError, AccessError, ...
        if (_.has(this.odooExceptionTitleMap, error.data.name)) {
            error = _.extend({}, error, {
                data: _.extend({}, error.data, {
                    message: error.data.arguments[0],
                    title: this.odooExceptionTitleMap[error.data.name],
                }),
            });
            this.show_warning(error);
            return;
        }

        // Any other Python exception
        this.show_error(error);
    },
    show_warning: function (error, options) {
        if (!active) {
            return;
        }
        var message = error.data ? error.data.message : error.message;
        var title = _t("Something went wrong !");
        if (error.type) {
            title = _.str.capitalize(error.type);
        } else if (error.data && error.data.title) {
            title = _.str.capitalize(error.data.title);
        }
        return this._displayWarning(message, title, options);
    },
    show_error: function (error) {
        if (!active) {
            return;
        }
        error.traceback = error.data.debug;
        var dialogClass = error.data.context && ErrorDialogRegistry.get(error.data.context.exception_class) || ErrorDialog;
        var dialog = new dialogClass(this, {
            title: _.str.capitalize(error.type) || _t("Odoo Error"),
        }, error);


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

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {string} message
     * @param {string} title
     * @param {Object} options
     */
    _displayWarning: function (message, title, options) {
        return new WarningDialog(this, Object.assign({}, options, {
            title,
        }), {
            message,
        }).open();
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
        var additional_context = _.extend({}, this.context, error.data.arguments[3]);

        new WarningDialog(this, {
            title: _.str.capitalize(error.type) || _t("Odoo Warning"),
            buttons: [
                {text: error.data.arguments[2], classes : "btn-primary", click: function() {
                    self.do_action(
                        error.data.arguments[1],
                        {
                            additional_context: additional_context,
                        });
                        self.destroy();
                }, close: true},
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
            const notif = {
                type: _t("Odoo Session Expired"),
                message: _t("Your Odoo session expired. The current page is about to be refreshed."),
            };
            const options = {
                buttons: [{
                    text: _t("Ok"),
                    click: () => window.location.reload(true),
                    close: true
                }],
            };
            cm.show_warning(notif, options);
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
    disable: () => active = false,
};
});
