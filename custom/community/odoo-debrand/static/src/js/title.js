odoo.define('odoo-debrand.title', function(require) {
    var core = require('web.core');
    var utils = require('web.utils');
    var QWeb = core.qweb;
    var _t = core._t;
    var ajax = require('web.ajax');
    var Dialog = require('web.Dialog');
    var WebClient = require('web.AbstractWebClient');
    var CrashManager = require('web.CrashManager');
    var Model = require('web.Model');
    WebClient.include({
    init: function(parent) {
        this.client_options = {};
        this._super(parent);
        this.origin = undefined;
        this._current_state = null;
        this.menu_dm = new utils.DropMisordered();
        this.action_mutex = new utils.Mutex();
        var self = this;
        new Model("website").call("search_read",[[], ['company_name']]).then(function (res) {
            self.set('title_part', {"zopenerp": res && res[0] && res[0].company_name || ''});
        });
    },
    });
    CrashManager.include({
        show_warning: function(error) {
            if (!this.active) {
                return;
            }
            new Dialog(this, {
                size: 'medium',
                title: (_.str.capitalize(error.type) || _t("Warning")),
                subtitle: error.data.title,
                $content: $('<div>').html(QWeb.render('CrashManager.warning', {error: error}))
            }).open();
        },
        show_error: function(error) {
        if (!this.active) {
            return;
        }
        new Dialog(this, {
            title: _.str.capitalize(error.type),
            $content: QWeb.render('CrashManager.error', {error: error})
        }).open();
        },
        show_message: function(exception) {
            this.show_error({
                type: _t("Client Error"),
                message: exception,
                data: {debug: ""}
            });
        },
    });
});
