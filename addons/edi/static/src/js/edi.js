odoo.define('edi.EdiImport', ['web.core', 'web.Dialog', 'web.framework', 'web.Widget'], function (require) {
"use strict";

var core = require('web.core');
var Dialog = require('web.Dialog');
var framework = require('web.framework');
var Widget = require('web.Widget');

var _t = core._t;
var QWeb = core.qweb;

var EdiImport = Widget.extend({

    init: function(parent,url) {
        this._super();
        this.url = url;
    },
    start: function() {
        if (!this.session.session_is_valid()) {
            framework.redirect('/web/login?redir=' + encodeURIComponent(window.location));
        } else {
            this.show_import();
        }
    },

    show_import: function() {
        this.destroy_content();
        this.do_import();
    },

    destroy_content: function() {
        _.each(_.clone(this.getChildren()), function(el) {
            el.destroy();
        });
        this.$el.children().remove();
    },

    do_import: function() {
        this.rpc('/edi/import_edi_url', {url: this.url}).done(this.on_imported).fail(this.on_imported_error);
    },
    on_imported: function(response) {
        if ('action' in response) {
            this.rpc("/web/session/save_session_action", {the_action: response.action}).done(function(key) {
                window.location = "/#sa="+encodeURIComponent(key);
            });
        }
        else {
            new Dialog(this,{
                    title: 'Import Successful!',
                    buttons: {
                        Ok: function() {
                            this.parents('.modal').modal('hide');
                            window.location = "/";
                        }
                    }
                },$('<div>').html(_t('The document has been successfully imported!'))).open();
        }
    },
    on_imported_error: function(response){
        var self = this;
        var msg = _t("Sorry, the document could not be imported.");
        if (response.data.message) {
            msg += "\n " + _t("Reason:") + response.data.message;
        }
        var params = {error: response, message: msg};
        new Dialog(this,{
                title: _t("Document Import Notification"),
                buttons: {
                    Ok: function() { this.parents('.modal').modal('hide');}
                }
            },$(QWeb.render("CrashManager.warning", params))).open();
    }
});

return EdiImport;

});
