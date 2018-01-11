openerp.google_drive = function (instance, m) {
    var _t = instance.web._t,
        QWeb = instance.web.qweb;

    instance.web.Sidebar.include({
        start: function () {
            var self = this;
            var ids
            this._super.apply(this, arguments);
            var view = self.getParent();
            var result;
            if (view.fields_view.type == "form") {
                ids = []
                view.on("load_record", self, function (r) {
                    ids = [r.id]
                    self.add_gdoc_items(view, r.id)
                });
            }
        },
        add_gdoc_items: function (view, res_id) {
            var self = this;
            var gdoc_item = _.indexOf(_.pluck(self.items.other, 'classname'), 'oe_share_gdoc');
            if (gdoc_item !== -1) {
                self.items.other.splice(gdoc_item, 1);
            }
            if (res_id) {
                view.sidebar_eval_context().done(function (context) {
                    var ds = new instance.web.DataSet(this, 'google.drive.config', context);
                    ds.call('get_google_drive_config', [view.dataset.model, res_id, context]).done(function (r) {
                        if (!_.isEmpty(r)) {
                            _.each(r, function (res) {
                                var already_there = false;
                                for (var i = 0;i < self.items.other.length;i++){
                                    if (self.items.other[i].classname === "oe_share_gdoc" && self.items.other[i].label.indexOf(res.name) > -1){
                                        already_there = true;
                                        break;
                                    }
                                }
                                if (!already_there){
                                    self.add_items('other', [{
                                            label: res.name,
                                            config_id: res.id,
                                            res_id: res_id,
                                            res_model: view.dataset.model,
                                            callback: self.on_google_doc,
                                            classname: 'oe_share_gdoc'
                                        },
                                    ]);
                                }
                            })
                        }
                    });
                });
            }
        },

        fetch: function (model, fields, domain, ctx) {
            return new instance.web.Model(model).query(fields).filter(domain).context(ctx).all()
        },

        on_google_doc: function (doc_item) {
            var self = this;
            self.config = doc_item;
            var loaded = self.fetch('google.drive.config', ['google_drive_resource_id', 'google_drive_client_id'], [['id', '=', doc_item.config_id]])
                .then(function (configs) {
                var ds = new instance.web.DataSet(self, 'google.drive.config');
                ds.call('get_google_drive_url', [doc_item.config_id, doc_item.res_id,configs[0].google_drive_resource_id, self.dataset.context]).done(function (url) {
                    if (url){
                        window.open(url, '_blank');
                    }
                });
            });
        },

    });
};
