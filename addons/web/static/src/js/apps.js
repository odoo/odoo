odoo.define('web.Apps', function (require) {
"use strict";

var core = require('web.core');
var framework = require('web.framework');
var Model = require('web.DataModel');
var session = require('web.session');
var web_client = require('web.web_client');
var Widget = require('web.Widget');

var _t = core._t;

var apps_client = null;
var qweb = core.qweb;

var Apps = Widget.extend({
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
        if (apps_client) {
            return check_client_available(apps_client);
        } else {
            var Mod = new Model('ir.module.module');
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
                apps_client = client;
                return check_client_available(client);
            });
        }
    },

    destroy: function() {
        $(window).off("message." + this.uniq);
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
                var M = new Model(m.model);
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

    _on_update_count: function(m) {
        var self = this;
        var count = m.count;
        var get_upd_menu_id = function() {
            if (_.isUndefined(self._upd_menu_id)) {
                var IMD = new Model('ir.model.data');
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
            var $menu = web_client.menu.$secondary_menus.find(_.str.sprintf('a[data-menu=%s]', menu_id));
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
                $menu.append(qweb.render("Menu.needaction_counter", {widget: {needaction_counter: count}}));
            }
        });
    },

    start: function() {
        var self = this;
        var def = $.Deferred();
        self.get_client().then(function(client) {
            self.client = client;

            var qs = {db: client.dbname};
            if (session.debug) {
                qs.debug = session.debug;
            }
            var u = $.param.querystring(client.origin + "/apps/embed/client", qs);
            var css = {width: '100%', height: '750px'};
            self.$ifr = $('<iframe>').attr('src', u);

            self.uniq = _.uniqueId('apps');
            $(window).on("message." + self.uniq, self.proxy('_on_message'));

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

            self.on('message:update_count', self, self._on_update_count);

            self.on('message:blockUI', self, function() { framework.blockUI(); });
            self.on('message:unblockUI', self, function() { framework.unblockUI(); });
            self.on('message:warn', self, function(m) {self.do_warn(m.title, m.message, m.sticky); });

            self.$ifr.appendTo(self.$el).css(css).addClass('apps-client');

            def.resolve();
        }, function() {
            self.do_warn(_t('Odoo Apps will be available soon'), _t('Showing locally available modules'), true);
            return session.rpc('/web/action/load', {action_id: self.failback_action_id}).then(function(action) {
                return self.do_action(action);
            }).always(function () {
                def.reject();
            });
        });
        return def;
    },
});

var AppsUpdates = Apps.extend({
    remote_action_tag: 'loempia.embed.updates',
});

core.action_registry.add("apps", Apps);
core.action_registry.add("apps.updates", AppsUpdates);

return Apps;

});
