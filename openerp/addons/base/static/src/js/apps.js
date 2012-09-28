openerp.base = function(instance) {

    instance.base = {apps:{}};

    instance.base.apps.remote_instance = null;

    instance.base.apps.get_client = function() {
        // return the client via a deferred, resolved or rejected depending if the remote host is available or not.
        var check_client_available = function(client) {
            var d = $.Deferred();
            var i = new Image();
            i.onerror = function() {
                d.reject(client);
            };
            i.onload = function() {
                console.log('client is available', client);
                d.resolve(client);
            };
            i.src = _.str.sprintf('%s/web/static/src/img/sep-a.gif', client.origin);
            return d.promise();
        };
        if (instance.base.apps._client) {
            return check_client_available(instance.base.apps._client);
        } else {
            //var DEFAULT_SERVER = 'http://apps.openerp.com/loempia';           // PROD
            var DEFAULT_SERVER = 'http://apps.openerp.com:9069/loempia7';     // TEST
            //var DEFAULT_SERVER = 'http://localhost:8080/trunk_loempia7';        // DEV
            var ICP = new instance.web.Model('ir.config_parameter');
            return ICP.call('get_param', ['loempia.server', DEFAULT_SERVER]).pipe(function(u) {
                var link = $(_.str.sprintf('<a href="%s"></a>', u))[0];
                var host = _.str.sprintf('%s//%s', link.protocol, link.host);
                var dbname = link.pathname.substr(1);

                var login = (sessionStorage ? sessionStorage.getItem('loempia.login') : null) || 'anonymous';
                var passwd = (sessionStorage ? sessionStorage.getItem('loempia.passwd') : null) || 'anonymous';

                if (_.isNull(instance.base.apps.remote_instance)) {
                    instance.base.apps.remote_instance = new openerp.init();
                }
                var client = new instance.base.apps.remote_instance.web.EmbeddedClient(null, host,
                                                                         dbname, login, passwd);

                console.log('new client', client);
                instance.base.apps._client = client;
                return check_client_available(client);
            });
        }

    };

    instance.base.apps.Apps = instance.web.Widget.extend({
        template: 'EmptyComponent',

        remote_action_id: 'loempia.action_embed',
        failback_action_id: 'base.open_module_tree',

        init: function(parent, options) {
            this._super(parent);
            this.params = options;      // NOTE read by embedded client action
        },

        clean: function() {
            instance.base.apps.get_client().always(function(client) { client.destroy(); });
        },

        destroy: function() {
            this.clean();
            return this._super();
        },

        start: function() {
            var self = this;
            console.time('apps');
            console.time('client');
            console.log('Apps.start()');
            return instance.base.apps.get_client().
                done(function(client) {
                    console.timeEnd('client');
                    client.replace(self.$el).
                        done(function() {
                            client.$el.removeClass('openerp');
                            console.timeEnd('apps');
                            client.do_action(self.remote_action_id);
                        });
                }).
                fail(function(client) {
                    self.do_warn('Apps Server not reachable.', 'Showing local modules.', true);
                    self.do_action(self.failback_action_id);
                });
        },

        0:0
    });

    instance.base.apps.UpdatesAvailable = instance.base.apps.Apps.extend({
        remote_action_id: 'loempia.action_embed_updates'
    })

    instance.web.client_actions.add("apps", "instance.base.apps.Apps");
    instance.web.client_actions.add("apps.updates", "instance.base.apps.UpdatesAvailable");

};
