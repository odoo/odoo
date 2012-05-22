openerp.google_docs = function(instance, m) {
    instance.web.Sidebar = instance.web.Sidebar.extend({
        on_attachments_loaded: function(attachments) {
            self._super(attachements);
            // if attachment contains a google doc url do nothing
            // else
            this.sidebar.add_items('other', [
                { label: _t('Google Doc'), callback: self.on_google_doc },
            ]);
        },
        on_google_doc: function() {
            var self = this;
            var form = self.getParent();
            form.sidebar_context().then(function (context) {
                var ds = new instance.web.DataSet(this, 'google.docs', context);
                ds.call('doc_get', [form.view.dataset.model, [form.view.datarecord.id], 'text'], function(r) {
                    if (r == 'False') {
                        var params = {
                            error: response,
                            message: "The user google credentials are not set yet. Contact your administrator for help."
                        }
                        $(openerp.web.qweb.render("DialogWarning", params)).dialog({
                            title: "User Google credentials are not yet set.",
                            modal: true,
                        });
                    }
                    view.reload();
                });
            }
        }
};
