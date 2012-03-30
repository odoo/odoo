openerp.google_docs = function(instance, session) {


        instance.web.form.SidebarAttachments = instance.web.form.SidebarAttachments.extend({
            init: function() {
                this._super.apply(this, arguments);
                this.$element.delegate('.oe_google_docs_text_button', 'click', this.on_add_text_gdoc);
                var self = this;
                var config = new instance.web.DataSet(this, 'google.docs.config', this.view.dataset.get_context());
                config.call('get_config', [this.view.dataset.ids[this.view.dataset.index]], function(r) {
                    // if the configuration isn't set, the buttons should be hidden.
                    if (r==false) {
                        $('.oe_google_docs_text_button',this.$element).hide();
                        return;
                    }

                    var attachment = new instance.web.DataSet(this, 'ir.attachment', self.view.dataset.get_context());
                    attachment.call('copy_gdoc', [self.view.dataset.model, [self.view.datarecord.id]], function(res) {
                    });
                });
            },
            start: function() {
                this._super();
                console.log($('.oe_google_docs_text_button',this.$element))
                $('.oe_google_docs_text_button',this.$element)
            },
            on_add_text_gdoc: function() {
                var self = this;
                var $gdocbtn = this.$element.find('.oe_google_docs_text_button');
                $gdocbtn.attr('disabled', 'true').find('img, span').toggle();
                var ds = new instance.web.DataSet(this, 'google.docs', this.view.dataset.get_context());
                ds.call('doc_get', [this.view.dataset.model, [this.view.datarecord.id], 'text'], function(r) {
                    self.do_update();
                });
            },
        });
};

