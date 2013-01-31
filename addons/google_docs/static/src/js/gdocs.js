openerp.google_docs = function(instance, m) {
var _t = instance.web._t,
    QWeb = instance.web.qweb;

    instance.web.Sidebar.include({
        redraw: function() {
            var self = this;
            this._super.apply(this, arguments);
            self.$el.find('.oe_sidebar_add_attachment').after(QWeb.render('AddGoogleDocumentItem', {widget: self}))
            self.$el.find('.oe_sidebar_add_google_doc').on('click', function (e) {
                self.on_google_doc();
            });
        },
        on_google_doc: function() {
            var self = this;
            var view = self.getParent();
            var ids = ( view.fields_view.type != "form" )? view.groups.get_selection().ids : [ view.datarecord.id ];
            if( !_.isEmpty(ids) ){
                view.sidebar_eval_context().done(function (context) {
                    var ds = new instance.web.DataSet(this, 'ir.attachment', context);
                    ds.call('google_doc_get', [view.dataset.model, ids, context]).done(function(r) {
                        if (r == 'False') {
                            var params = {
                                error: response,
                                message: _t("The user google credentials are not set yet. Contact your administrator for help.")
                            }
                            $(openerp.web.qweb.render("DialogWarning", params)).dialog({
                                title: _t("User Google credentials are not yet set."),
                                modal: true,
                            });
                        }
                    }).done(function(r){
                        window.open(r.url,"_blank");
                        view.reload();
                    });
                });
            }
        }
    });
};
