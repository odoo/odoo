odoo.define('odoo-debrand-11.title', function (require) {
    "use strict";

    var core = require('web.core');
    var session = require('web.session');
    var WebClient = require('web.AbstractWebClient');
    var utils = require('web.utils');
    var config = require('web.config');
    var _t = core._t;

    var ajax = require('web.ajax');
    var Dialog = require('web.Dialog');
    var ServiceProviderMixin = require('web.ServiceProviderMixin');
    var KeyboardNavigationMixin = require('web.KeyboardNavigationMixin');
    var CrashManager = require('web.CrashManager').CrashManager; // We can import crash_manager also
    var CrashManagerDialog = require('web.CrashManager').CrashManagerDialog; // We can import crash_manager also
    var ErrorDialog = require('web.CrashManager').ErrorDialog; // We can import crash_manager also
    var WarningDialog = require('web.CrashManager').WarningDialog; // We can import crash_manager also
//    var MailBotService = require('mail_bot.MailBotService').MailBotService; // We can import crash_manager also
    var concurrency = require('web.concurrency');
    var mixins = require('web.mixins');

    var QWeb = core.qweb;
    var _t = core._t;
    var _lt = core._lt;

    let active = true;


    WebClient.include({
        init: function (parent) {
            this._super(parent);
            var self = this;
            // Rpc call to fetch the compant name from model
            this._rpc({
                fields: ['company_name',],
                domain: [],
                model: 'website',
                method: 'search_read',
                limit: 1,
                context: session.user_context,
            }).then(function (result) {
                self.set(
                    'title_part',
                    {"zopenerp": result && result[0] && result[0].company_name || ''});
            });
        },
        start: function () {
            var self = this;
            this.$el.toggleClass('o_touch_device', config.device.touch);
            this.on("change:title_part", this, this._title_changed);
            this._title_changed();

            var state = $.bbq.getState();
            var current_company_id = session.user_companies.current_company[0]
            if (!state.cids) {
                state.cids = utils.get_cookie('cids') !== null ? utils.get_cookie('cids') : String(current_company_id);
            }
            var stateCompanyIDS = _.map(state.cids.split(','), function (cid) { return parseInt(cid) });
            var userCompanyIDS = _.map(session.user_companies.allowed_companies, function(company) {return company[0]});
            // Check that the user has access to all the companies
            if (!_.isEmpty(_.difference(stateCompanyIDS, userCompanyIDS))) {
                state.cids = String(current_company_id);
                stateCompanyIDS = [current_company_id]
            }
            // Update the user context with this configuration
            session.user_context.allowed_company_ids = stateCompanyIDS;
            $.bbq.pushState(state);
            // Update favicon
            $("link[type='image/x-icon']").attr('href', '/web/image/website/' + String(stateCompanyIDS[0]) + '/favicon/')

            return session.is_bound
                .then(function () {
                    self.$el.toggleClass('o_rtl', _t.database.parameters.direction === "rtl");
                    self.bind_events();
                    return Promise.all([
                        self.set_action_manager(),
                        self.set_loading()
                    ]);
                }).then(function () {
                    if (session.session_is_valid()) {
                        return self.show_application();
                    } else {
                        // database manager needs the webclient to keep going even
                        // though it has no valid session
                        return Promise.resolve();
                    }
                }).then(function () {
                    // Listen to 'scroll' event and propagate it on main bus
                    self.action_manager.$el.on('scroll', core.bus.trigger.bind(core.bus, 'scroll'));
                    core.bus.trigger('web_client_ready');
                    odoo.isReady = true;
                    if (session.uid === 1) {
                        self.$el.addClass('o_is_superuser');
                    }
                });
        },

    });
    CrashManager.include({
        init: function (parent) {
            var self = this;
            active = true;
            this.isConnected = true;
            this._super.apply(this, arguments);
//
            // crash manager integration
//            core.bus.on('rpc_error', this, this.rpc_error);
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
                            type: _t("Client Error"),
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
                        type: _t("Client Error"),
                        message: message,
                        data: {debug: file + ':' + line + "\n" + _t('Traceback:') + "\n" + traceback},
                    });
                }
            };
//
            // listen to unhandled rejected promises, and throw an error when the
            // promise has been rejected due to a crash
            core.bus.on('crash_manager_unhandledrejection', this, function (ev) {
                if (ev.reason && ev.reason instanceof Error) {
                    var traceback = ev.reason.stack;
                    self.show_error({
                        type: _t("Client Error"),
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
//        rpc_error: function(error) {
//        // Some qunit tests produces errors before the DOM is set.
//        // This produces an error loop as the modal/toast has no DOM to attach to.
//        if (!document.body) {
//            return;
//        }
//        var map_title = {
//            access_denied: _lt("Access Denied"),
//            access_error: _lt("Access Error"),
//            except_orm: _lt("Global Business Error"),
//            missing_error: _lt("Missing Record"),
//            user_error: _lt("User Error"),
//            validation_error: _lt("Validation Error"),
//            warning: _lt("Warning"),
//        };
//        if (!active) {
//            return;
//        }
//        if (this.connection_lost) {
//            return;
//        }
//        if (error.code === -32098) {
//            this.handleLostConnection();
//            return;
//        }
//        var handler = core.crash_registry.get(error.data.name, true);
//        if (handler) {
//            new (handler)(this, error).display();
//            return;
//        }
//        if (_.has(map_title, error.data.exception_type)) {
//            if (error.data.exception_type === 'except_orm') {
//                if (error.data.arguments[1]) {
//                    error = _.extend({}, error,
//                                {
//                                    data: _.extend({}, error.data,
//                                        {
//                                            message: error.data.arguments[1],
//                                            title: error.data.arguments[0] !== 'Warning' ? error.data.arguments[0] : '',
//                                        })
//                                });
//                }
//                else {
//                    error = _.extend({}, error,
//                                {
//                                    data: _.extend({}, error.data,
//                                        {
//                                            message: error.data.arguments[0],
//                                            title:  '',
//                                        })
//                                });
//                }
//            }
//            else {
//                error = _.extend({}, error,
//                            {
//                                data: _.extend({}, error.data,
//                                    {
//                                        message: error.data.arguments[0],
//                                        title: map_title[error.data.exception_type] !== 'Warning' ? map_title[error.data.exception_type] : '',
//                                    })
//                            });
//            }
//            this.show_warning(error);
//        } else {
//            this.show_error(error);
//        }
//    },
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
        let ttype = "type" in error;
        let mmessage = "message" in error;
        if (ttype) {
            if ( error.type.includes('Odoo')){
            error.type = error.type.replace('Odoo', '')
            }
        }
        else {
            error.type = _t("Error")
        }
        if (mmessage){
            if ( error.message.includes('Odoo')){
            error.message = error.message.replace('Odoo', '')
            }
        }
        this._super(error)
    },
    show_message: function(exception) {
        return this.show_error({
            type: _t("Client Error"),
            message: exception,
            data: {debug: ""}
        });
    },
});
Dialog.include({
    init: function (parent, options) {
            var self = this;
            this._super(parent);
            this._opened = new Promise(function (resolve) {
                self._openedResolver = resolve;
            });
            options = _.defaults(options || {}, {
                title: _t(' '), subtitle: '',
                size: 'large',
                fullscreen: false,
                dialogClass: '',
                $content: false,
                buttons: [{text: _t("Ok"), close: true}],
                technical: true,
                $parentNode: false,
                backdrop: 'static',
                renderHeader: true,
                renderFooter: true,
                onForceClose: false,
            });

            this.$content = options.$content;
            this.title = options.title;
            this.subtitle = options.subtitle;
            this.fullscreen = options.fullscreen;
            this.dialogClass = options.dialogClass;
            this.size = options.size;
            this.buttons = options.buttons;
            this.technical = options.technical;
            this.$parentNode = options.$parentNode;
            this.backdrop = options.backdrop;
            this.renderHeader = options.renderHeader;
            this.renderFooter = options.renderFooter;
            this.onForceClose = options.onForceClose;

            core.bus.on('close_dialogs', this, this.destroy.bind(this));
        },
    });
});