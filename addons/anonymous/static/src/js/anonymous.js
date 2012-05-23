openerp.anonymous = function(instance) {
    // TODO change User menu

    instance.web.WebClient.include({
        show_login: function() {
            var self = this, _super = this._super;
            this.login.load_db_list().then(function() {
                var dblist = self.login._db_list;
                if (dblist && dblist.length === 1) {
                    // XXX get login/pass from server (via a rpc call) ?
                    self.login.do_login(dblist[0], 'anonymous', 'anonymous').fail(function() {
                        _super.apply(self, []);
                    });
                } else {
                    _super.apply(self, []);
                }
            });
        },
    });

};
