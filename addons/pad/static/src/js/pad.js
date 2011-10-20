
openerp.pad = function(instance) {

var QWeb = instance.web.qweb;
QWeb.add_template('/pad/static/src/xml/pad.xml');

instance.web.form.SidebarAttachments = instance.web.form.SidebarAttachments.extend({

    pad_prefix: undefined,

    on_add_pad: function() {
        var self = this;
        var $padbtn = this.$element.find('button.pad');
        $padbtn.attr('disabled', 'true').find('img, span').toggle();

        this.do_load_pad_prefix(function() {
            var attachment = new instance.web.DataSet(self, 'ir.attachment', self.view.dataset.get_context());
            var r = (((1+Math.random())*0x10000)|0).toString(16).substring(1);
            attachment.create({
                res_model: self.view.dataset.model,
                res_id: self.view.datarecord.id,
                type: 'url',
                name: 'Pad',
                url: self.pad_prefix + r,
            }, function() {
                self.do_update();
            });
        });

    },

    do_load_pad_prefix: function(continuation) {
        var self = this;
        if (this.pad_prefix === undefined) {
            var user = new instance.web.DataSet(this, 'res.users', this.view.dataset.get_context());
            var company = new instance.web.DataSet(this, 'res.company', this.view.dataset.get_context());
            user.read_ids([this.session.uid], ['company_id'], function(result) {
                company.read_ids([result[0].company_id[0]], ['pad_index'], function(result) {
                    var pad_index = _(result[0].pad_index).strip().replace(/\/$/, "");;
                    if (pad_index) {
                        self.pad_prefix = _('%s/%s-%s-%d-').sprintf(pad_index, self.session.db, self.view.dataset.model, self.view.datarecord.id);
                    } else {
                        self.pad_prefix = null;
                    }
                    continuation();
                });
            });
        } else {
            continuation();
        }
    },

    on_attachments_loaded: function(attachments) {
        this._super(attachments);
        var self = this;
        this.do_load_pad_prefix(function() {
            var $padbtn = self.$element.find('button.pad');
            var is_pad = function(a) {
                return a.type == 'url' && _(a.url).startsWith(self.pad_prefix);
            };
            if (!self.pad_prefix || _.any(attachments, is_pad)) {
                $padbtn.hide();
            } else {
                $padbtn.show().click(self.on_add_pad);
            }
        });

    },
});

};
