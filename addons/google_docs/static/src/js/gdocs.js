openerp.google_docs = function(instance, m) {
var _t = instance.web._t;

    instance.web.Sidebar = instance.web.Sidebar.extend({
        on_attachments_loaded: function(attachments) {
            var self = this;
            self._super(attachments);
            // if attachment contains a google doc url do nothing
            // else display a button to create a google doc
            var flag = false;
            _.each(attachments, function(i) {
                if (i.url && i.url.match('/docs.google.com/')) { flag = true; }
            });
            if (! flag) {
                this.add_items('files', [
                    { label: _t('Google Doc'), callback: self.on_google_doc },
                ]);
            }
        },
        on_google_doc: function() {
            var self = this;
            var form = self.getParent();
            form.sidebar_context().then(function (context) {
                var ds = new instance.web.DataSet(this, 'ir.attachment', context);
                ds.call('google_doc_get', [form.dataset.model, [form.datarecord.id], context], function(r) {
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
                    form.reload();
                });
            })
        }
    })
}
