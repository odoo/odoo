openerp.base = function(instance) {

    instance.base = {};
    instance.base.Apps = instance.web.Widget.extend({
        template: 'EmptyComponent',
        init: function(parent, options) {
            this._super(parent);
            this.params = options;      // NOTE read by embeded client action
            this.clean();
            // create a new instance
            this.remote_instance = new openerp.init();
        },

        clean: function() {
            if (this.client) {
                this.client.destroy();
            }
        },

        destroy: function() {
            this.clean();
            //delete this.remote_instance;
            return this._super();
        },

        _get_options: function() {
            var self = this;
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

                return {
                   url: host,
                   dbname: dbname,
                   login: login,
                   password: passwd,
                   action_id: 'loempia.action_embed'
                };
            });
        },

        start: function() {
            return this._get_options().then(this.proxy('_connect'));
        },
        _connect: function(options) {
            var self = this;
            // before creating the client, check the connectivity...
            var i = new Image();
            i.onerror = function() {
                self.do_warn(_.str.sprintf('Apps Server %s not available.', options.url), 'Showing local modules.', true);
                self.do_action('base.open_module_tree');
            };
            i.onload = function() {

                var client = self.client = new self.remote_instance.web.EmbeddedClient(null, options.url,
                                                                         options.dbname, options.login, options.password,
                                                                         options.action_id);

                client.replace(self.$el).
                    done(function() {
                        client.$el.removeClass('openerp');
                    });
            };
            i.src = _.str.sprintf('%s/web/static/src/img/sep-a.gif', options.url);
        }
    });

    instance.web.client_actions.add("apps", "instance.base.Apps");
};
