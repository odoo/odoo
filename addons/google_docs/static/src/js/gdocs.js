openerp.google_docs = function(instance, m) {
var QWeb = instance.web.qweb,
    _t = instance.web._t;

    instance.web.Sidebar = instance.web.Sidebar.extend({
       redraw: function() {
           var self = this;
           this._super.apply(this, arguments);
           self.$el.find('.oe_sidebar_add_attachment').after(QWeb.render('Google_doc', {widget: self}))
           self.$el.find('.oe_sidebar_add_google_doc').on('click', function (e) {
                                self.on_google_doc();
            });
        },
        on_google_doc: function() {
            var self = this;
            var form = self.getParent();
            form.sidebar_context().then(function (context) {
                var ds = new instance.web.DataSet(this, 'ir.attachment', context);
                def = ds.call('google_doc_get', [form.dataset.model, [form.datarecord.id], context], function(r) {
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
                    
                }).done(function(){ 
                        form.reload();
                   });
            })
        }
    })
}
