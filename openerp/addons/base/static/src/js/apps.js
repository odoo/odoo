openerp.base = function(instance) {

    instance.base = {};
    instance.base.Apps = instance.web.Widget.extend({
        template: 'EmptyComponent',
        init: function(parent, options) {
            this._super(parent);
            this.params = options;
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
            this._super();
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
            this.options = options;

            var client = this.client = new this.remote_instance.web.EmbeddedClient(null, this.options.url,
                                                                     this.options.dbname, this.options.login, this.options.password,
                                                                     this.options.action_id);
            client.on('connection_failed', this, this.action_fallback);
            //this.client = client;

            client.replace(this.$el).
                done(function() {
                    client.$el.removeClass('openerp');
                }).
                fail(function() {
                    console.log('fail', this);
                    alert('fail');
                });
        },

        action_fallback: function() {
            // TODO show flash message
            this.do_warn(this.options.url + ' unreachable');
            this.do_action('base.action_modules');
        }
    });

    instance.web.client_actions.add("apps", "instance.base.Apps");
};
