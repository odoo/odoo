openerp.google_docs = function (instance, m) {
    var _t = instance.web._t,
        QWeb = instance.web.qweb;

    instance.web.Sidebar.include({
        start: function () {
            var self = this;
            var ids
            this._super.apply(this, arguments);
            var view = self.getParent();
            var result;
            this.check_url();
            if (view.fields_view.type == "form") {
                ids = []
                view.on("load_record", self, function (r) {
                    ids = [r.id]
                    self.add_gdoc_items(view, r.id)
                });
            }
        },
        check_url: function () {
            /* This function check URL and if there is 'state' object (dictionary) sent by google,
             * it will fetch file 'exportIds' from 'state' object and redirect to corresponding record in openerp
             */ 
            self = this;
            var state = this.getUrlVars();
            if (state) {
                file_obj = JSON.parse(state);
                var loaded = self.fetch('ir.attachment', ['res_model', 'res_id', 'url', 'name'], [['url', 'ilike', '%' + file_obj.exportIds[0] + '%']])
                    .then(function (att) {
                    console.log(att);
                    if (att.length != 0) {
                        url = window.location.href.replace(/(\&)(.*)/, "");
                        url = url + "#id=" + att[0].res_id + "&model=" + att[0].res_model;
                        $('body').hide();
                        window.open(url, '_self');
                    }
                });
            }
        },
        getUrlVars: function () {
            var parts=unescape(window.location.href);
            var n=parts.match(/(state=)(.*})/);
            if(n && n.length>2){
                return n[2];
            }
            else{
                return false
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
                    var ds = new instance.web.DataSet(this, 'google.docs.config', context);
                    ds.call('get_google_docs_config', [view.dataset.model, res_id, context]).done(function (r) {
                        if (!_.isEmpty(r)) {
                            _.each(r, function (res) {
                                var g_item = _.indexOf(_.pluck(self.items.other, 'label'), res.name);
                                if (g_item !== -1) {
                                    self.items.other.splice(g_item, 1);
                                }
                                self.add_items('other', [{
                                        label: res.name,
                                        config_id: res.id,
                                        res_id: res_id,
                                        res_model: view.dataset.model,
                                        callback: self.on_google_doc,
                                        classname: 'oe_share_gdoc'
                                    },
                                ]);
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
            var loaded = self.fetch('google.docs.config', ['gdocs_resource_id', 'google_client_id'], [['id', '=', doc_item.config_id]])
                .then(function (configs) {
                var ds = new instance.web.DataSet(self, 'google.docs.config');
                ds.call('get_google_doc_name', [[doc_item.config_id], doc_item.res_id]).done(function (r) {
                    if (!_.isEmpty(r)) {
                        self.OAUTHURL = 'https://accounts.google.com/o/oauth2/auth?';
                        self.VALIDURL = 'https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=';
                        self.SCOPES = 'https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/drive.install';
                        self.CLIENT_ID = configs[0].google_client_id;
                        self.GDOC_NAME = r[doc_item.config_id]['name'];
                        self.GDOCS_TEMPLATE_ID = configs[0].gdocs_resource_id;
                        self.GDOC_URL = r[doc_item.config_id]['url'];
                        self.handleClientLoad();
                    }
                });
            });
        },

        handleClientLoad: function () {
            var self = this;
            window.setTimeout(function () {
                self.checkAuth(self)
            }, 1);
        },

        checkAuth: function (self) {
            gapi.auth.authorize({
                'client_id': self.CLIENT_ID,
                'scope': self.SCOPES,
                'immediate': true
            }, function (authResult) {
                self.handleAuthResult(self, authResult)
            });
        },

        handleAuthResult: function (self, authResult) {

            if (authResult && !authResult.error) {
                self.clientLoad(self);
            } else {
                gapi.auth.authorize({
                    'client_id': self.CLIENT_ID,
                    'scope': self.SCOPES,
                    'immediate': false
                }, function (authResult) {
                    self.handleAuthResult(self, authResult)
                });
            }
        },

        clientLoad: function (self) {
            gapi.client.load('drive', 'v2', function () {
                if (self.GDOC_URL == false) {
                    self.copyFile(self.config, self.GDOCS_TEMPLATE_ID, self.GDOC_NAME);
                } else {
                    window.open(self.GDOC_URL, '_blank');
                }
            });
        },

        copyFile: function (config, originFileId, copyTitle) {
            discription = window.location.href;
            discription = discription.replace(/(\&)?menu_id(.*)/, "");
            discription = discription.replace(/(\&)?action(.*)/, "");
            var body = {
                'title': copyTitle,
                "description": 'Click Below link for open record in OpenERP\n' + discription,
            };
            var request = gapi.client.drive.files.copy({
                'fileId': originFileId,
                'resource': body
            });
            request.execute(function (resp) {
                console.log('Copy ID: ' + resp.id);
                var get_new_file = gapi.client.drive.files.get({
                    'fileId': resp.id
                });
                get_new_file.execute(function (file) {
                    var ds = new instance.web.DataSet(self, 'ir.attachment');
                    vals = {
                        'res_model': config.res_model,
                        'res_id': config.res_id,
                        'type': 'url',
                        'name': copyTitle,
                        'url': file.alternateLink
                    }
                    ds.call('create', [vals]).done(function (r) {
                        window.open(file.alternateLink, '_blank');
                    });
                });
            });
        },
    });
};