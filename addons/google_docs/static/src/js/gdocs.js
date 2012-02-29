openerp.google_docs = function(instance, session) {

instance.web.form.SidebarAttachments = instance.web.form.SidebarAttachments.extend({
    init: function() {
        this._super.apply(this, arguments);
                this.$element.delegate('.oe_google_docs_button', 'click', this.on_add_gdoc);
    },
    on_add_gdoc: function() {
        var self = this;
        var $gdocbtn = this.$element.find('.oe_google_docs_button');
        $gdocbtn.attr('disabled', 'true').find('img, span').toggle();
        var ds = new instance.web.DataSet(this, 'google.docs', this.view.dataset.get_context());
            ds.call('doc_get', [this.view.dataset.model, [this.view.datarecord.id]], function(r) {
            self.do_update();
        });
    }
});

};

