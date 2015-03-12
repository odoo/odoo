openerp.base = function(instance) {

    instance.base.apps_client = null;

    var _t = instance.web._t;

    instance.base.Apps = instance.web.Widget.extend({
        template: 'EmptyComponent',
        remote_action_tag: 'loempia.embed',
        failback_action_id: 'base.open_module_tree',

        init: function(parent, action) {
            this._super(parent, action);
            var options = action.params || {};
            this.params = options;  // NOTE forwarded to embedded client action
        },

        get_client: function() {
            // return the client via a deferred, resolved or rejected depending if the remote host is available or not.
            var check_client_available = function(client) {
                var d = $.Deferred();
                var i = new Image();
                i.onerror = function() {
                    d.reject(client);
                };
                i.onload = function() {
                    d.resolve(client);
                };
                var ts = new Date().getTime();
                i.src = _.str.sprintf('%s/web/static/src/img/sep-a.gif?%s', client.origin, ts);
                return d.promise();
            };
            if (instance.base.apps_client) {
                return check_client_available(instance.base.apps_client);
            } else {
                var Mod = new instance.web.Model('ir.module.module');
                return Mod.call('get_apps_server').then(function(u) {
                    var link = $(_.str.sprintf('<a href="%s"></a>', u))[0];
                    var host = _.str.sprintf('%s//%s', link.protocol, link.host);
                    var dbname = link.pathname;
                    if (dbname[0] === '/') {
                        dbname = dbname.substr(1);
                    }
                    var client = {
                        origin: host,
                        dbname: dbname
                    };
                    instance.base.apps_client = client;
                    return check_client_available(client);
                });
            }
        },

        destroy: function() {
            $(window).off("message.apps");
            if (this.$ifr) {
                this.$ifr.remove();
                this.$ifr = null;
            }
            return this._super();
        },

        _on_message: function($e) {
            var self = this, client = this.client, e = $e.originalEvent;

            if (e.origin !== client.origin) {
                return;
            }

            var dispatcher = {
                'event': function(m) { self.trigger('message:' + m.event, m); },
                'action': function(m) {
                    self.do_action(m.action).then(function(r) {
                        var w = self.$ifr[0].contentWindow;
                        w.postMessage({id: m.id, result: r}, client.origin);
                    });
                },
                'rpc': function(m) {
                    self.session.rpc.apply(self.session, m.args).then(function(r) {
                        var w = self.$ifr[0].contentWindow;
                        w.postMessage({id: m.id, result: r}, client.origin);
                    });
                },
                'Model': function(m) {
                    var M = new instance.web.Model(m.model);
                    M[m.method].apply(M, m.args).then(function(r) {
                        var w = self.$ifr[0].contentWindow;
                        w.postMessage({id: m.id, result: r}, client.origin);
                    });
                },
            };
            // console.log(e.data);
            if (!_.isObject(e.data)) { return; }
            if (dispatcher[e.data.type]) {
                dispatcher[e.data.type](e.data);
            }
        },

        start: function() {
            var self = this;
            return self.get_client().
                done(function(client) {
                    self.client = client;

                    var qs = (instance.session.debug ? 'debug&' : '') + 'db=' + client.dbname;
                    var u = client.origin + '/apps/embed/client?' + qs;
                    var css = {width: '100%', height: '400px'};
                    self.$ifr = $('<iframe>').attr('src', u);

                    $(window).on("message.apps", self.proxy('_on_message'));

                    self.on('message:ready', self, function(m) {
                        var w = this.$ifr[0].contentWindow;
                        var act = {
                            type: 'ir.actions.client',
                            tag: this.remote_action_tag,
                            params: _.extend({}, this.params, {
                                db: this.session.db,
                                origin: this.session.origin,
                            })
                        };
                        w.postMessage({type:'action', action: act}, client.origin);
                    });

                    self.on('message:set_height', self, function(m) {
                        this.$ifr.height(m.height);
                    });

                    self.on('message:update_count', self, function(m) {
                        var count = m.count
                        var get_upd_menu_id = function() {
                            if (_.isUndefined(self._upd_menu_id)) {
                                var IMD = new instance.web.Model('ir.model.data');
                                return IMD.call('get_object_reference', ['base', 'menu_module_updates']).then(function(r) {
                                    var mid = r[1];
                                    if(r[0] !== 'ir.ui.menu') {
                                        // invalid reference, return null
                                        mid = null;
                                    }
                                    self._upd_menu_id = mid;
                                    return mid;
                                });
                            } else {
                                return $.Deferred().resolve(self._upd_menu_id).promise();
                            }
                        };

                        $.when(get_upd_menu_id()).done(function(menu_id) {
                            if (_.isNull(menu_id)) {
                                return;
                            }
                            var $menu = instance.webclient.menu.$secondary_menus.find(_.str.sprintf('a[data-menu=%s]', menu_id));
                            if ($menu.length === 0) {
                                return;
                            }
                            if (_.isUndefined(count)) {
                                count = 0;
                            }
                            var needupdate = $menu.find('#menu_counter');
                            if (needupdate && needupdate.length !== 0) {
                                if (count > 0) {
                                    needupdate.text(count);
                                } else {
                                    needupdate.remove();
                                }
                            } else if (count > 0) {
                                $menu.append(instance.web.qweb.render("Menu.needaction_counter", {widget: {needaction_counter: count}}));
                            }
                        });
                    });

                    self.on('message:blockUI', self, function() { instance.web.blockUI(); });
                    self.on('message:unblockUI', self, function() { instance.web.unblockUI(); });
                    self.on('message:warn', self, function(m) {instance.webclient.do_warn(m.title, m.message, m.sticky); });

                    self.$ifr.appendTo(self.$el).css(css).addClass('apps-client');
                }).
                fail(function(client) {
                    self.do_warn(_t('Odoo Apps will be available soon'), _t('Showing locally available modules'), true);
                    self.rpc('/web/action/load', {action_id: self.failback_action_id}).done(function(action) {
                        self.do_action(action);
                        instance.webclient.menu.open_action(action.id);
                    });
                });
        },
    });

    instance.base.AppsUpdates = instance.base.Apps.extend({
        remote_action_tag: 'loempia.embed.updates',
    });

    instance.web.client_actions.add("apps", "instance.base.Apps");
    instance.web.client_actions.add("apps.updates", "instance.base.AppsUpdates");

};
