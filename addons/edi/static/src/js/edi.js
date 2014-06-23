openerp.edi = function(instance) {
var _t = instance.web._t;
instance.edi = {};


instance.edi.EdiImport = instance.web.Widget.extend({

    init: function(parent,url) {
        this._super();
        this.url = url;
    },
    start: function() {
        if (!this.session.session_is_valid()) {
            instance.redirect('/web/login?redir=' + encodeURIComponent(window.location));
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
            new instance.web.Dialog(this,{
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
        new instance.web.Dialog(this,{
                title: _t("Document Import Notification"),
                buttons: {
                    Ok: function() { this.parents('.modal').modal('hide');}
                }
            },$(instance.web.qweb.render("CrashManager.warning", params))).open();
    }
});

instance.edi.edi_import = function (url) {
    instance.session.session_bind().done(function () {
        new instance.edi.EdiImport(null,url).appendTo($("body").addClass('openerp'));
    });
}

};
// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
