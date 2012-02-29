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
        new openerp.sessions.session0.web.DataSet(this, 'google.docs').call('doc_get', [this.view.datarecord.id, this.view.dataset.get_context()], function(r) {
            console.log(r);
            self.do_update();
        });
    }
});

};

