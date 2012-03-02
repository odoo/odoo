openerp.google_docs = function(instance, session) {


        instance.web.form.SidebarAttachments = instance.web.form.SidebarAttachments.extend({
            init: function() {
                this._super.apply(this, arguments);
                this.$element.delegate('.oe_google_docs_text_button', 'click', this.on_add_text_gdoc);
                this.$element.delegate('.oe_google_docs_spreadsheet_button', 'click', this.on_add_spreadsheet_gdoc);
                this.$element.delegate('.oe_google_docs_slide_button', 'click', this.on_add_slide_gdoc);
            },
            on_add_text_gdoc: function() {
                console.log('on_add_text_gdoc:');
                var self = this;
                var $gdocbtn = this.$element.find('.oe_google_docs_text_button');
                $gdocbtn.attr('disabled', 'true').find('img, span').toggle();
                var ds = new instance.web.DataSet(this, 'google.docs', this.view.dataset.get_context());
                ds.call('doc_get', [this.view.dataset.model, [this.view.datarecord.id], 'text'], function(r) {
                    console.log('on_add_text_gdoc: return');
                    self.do_update();
                });
            },
            on_add_spreadsheet_gdoc: function() {
                console.log('on_add_spreadsheet_gdoc:');
                var self = this;
                var $gdocbtn = this.$element.find('.oe_google_docs_spreadsheet_button');
                $gdocbtn.attr('disabled', 'true').find('img, span').toggle();
                var ds = new instance.web.DataSet(this, 'google.docs', this.view.dataset.get_context());
                console.log('on_add_spreadsheet_gdoc:');
                ds.call('doc_get', [this.view.dataset.model, [this.view.datarecord.id], 'spreadsheet'], function(r) {
                    console.log('on_add_spreadsheet_gdoc: return');
                    self.do_update();
                });
            },
            on_add_slide_gdoc: function() {
                console.log ('on_add_slide_gdoc:');
                var self = this;
                var $gdocbtn = this.$element.find('.oe_google_docs_slide_button');
                $gdocbtn.attr('disabled', 'true').find('img, span').toggle();
                var ds = new instance.web.DataSet(this, 'google.docs', this.view.dataset.get_context());
                ds.call('doc_get', [this.view.dataset.model, [this.view.datarecord.id], 'slide'], function(r) {
                    console.log('on_add_slide_gdoc: return');
                    self.do_update();
                });
            }
        });
};

