openerp.web_default_home = function (openerp) {
    var QWeb = openerp.web.qweb;
    QWeb.add_template('/web_default_home/static/src/xml/web_default_home.xml');

    openerp.web_default_home = {
        applications: [
            [
                {
                    module: 'crm', name: 'CRM',
                    help: "Acquire leads, follow opportunities, manage prospects and phone calls, \u2026"
                }, {
                    module: 'sale', name: 'Sales',
                    help: "Do quotations, follow sales orders, invoice and control deliveries"
                }, {
                    module: 'account_voucher', name: 'Invoicing',
                    help: "Send invoice, track payments and reminders"
                }, {
                    module: 'project', name: 'Projects',
                    help: "Manage projects, track tasks, invoice task works, follow issues, \u2026"
                }
            ], [
                {
                    module: 'purchase', name: 'Purchase',
                    help: "Do purchase orders, control invoices and reception, follow your suppliers, \u2026"
                }, {
                    module: 'stock', name: 'Warehouse',
                    help: "Track your stocks, schedule product moves, manage incoming and outgoing shipments, \u2026"
                }, {
                    module: 'hr', name: 'Human Resources',
                    help: "Manage employees and their contracts, follow laves, recruit people, \u2026"
                }, {
                    module: 'point_of_sale', name: 'Point of Sales',
                    help: "Manage shop sales, use touch-screen POS"
                }
            ], [
                {
                    module: 'profile_tools', name: 'Extra Tools',
                    help: "Track ideas, manage lunch, create surveys, share data"
                }, {
                    module: 'mrp', name: 'Manufacturing',
                    help: "Manage your manufacturing, control your supply chain, personalize master data, \u2026"
                }, {
                    module: 'marketing', name: 'Marketing',
                    help: "Manage campaigns, follow activities, automate emails, \u2026"
                }, {
                    module: 'knowledge', name: 'Knowledge',
                    help: "Track your documents, browse your files, \u2026"
                }
            ]
        ]
    };

    openerp.web.WebClient.include({
        default_home: function () {
            var self = this,
                // resig class can't handle _super in async contexts, by the
                // time async callback comes back, _super has already been
                // reset to a baseline value of this.prototype (or something
                // like that)
                old_home = this._super;
            var Installer = new openerp.web.DataSet(
                    this, 'base.setup.installer');
            Installer.call('already_installed', [], function (installed_modules) {
                if (!_(installed_modules).isEmpty()) {
                    return old_home.call(self);
                }
                self.action_manager.do_action({
                    type: 'ir.actions.client',
                    tag: 'home.default'
                })
            }, function (err, event) {
                event.preventDefault();
                return old_home.call(self);
            });
        }
    });

    openerp.web.client_actions.add(
        'home.default', 'openerp.web_default_home.DefaultHome');
    openerp.web_default_home.DefaultHome = openerp.web.View.extend({
        template: 'StaticHome',
        start: function () {
            var r = this._super(), self = this;
            this.$element.delegate('.oe-static-home-tile-text button', 'click', function () {
                self.install_module($(this).val());
            });
            return r;
        },
        render: function () {
            return this._super({
                url: window.location.protocol + '//' + window.location.host + window.location.pathname,
                session: this.session,
                rows: openerp.web_default_home.applications
            })
        },
        install_module: function (module_name) {
            var self = this;
            var Modules = new openerp.web.DataSetSearch(
                this, 'ir.module.module', null,
                [['name', '=', module_name], ['state', '=', 'uninstalled']]);
            var Upgrade = new openerp.web.DataSet(this, 'base.module.upgrade');

            $.blockUI({message:'<img src="/web/static/src/img/throbber2.gif">'});
            Modules.read_slice(['id'], {}, function (records) {
                if (!(records.length === 1)) { return; }
                Modules.call('state_update',
                    [_.pluck(records, 'id'), 'to install', ['uninstalled']],
                    function () {
                        Upgrade.call('upgrade_module', [[]], function () {
                            self.run_configuration_wizards();
                        });
                    }
                )
            });
        },
        run_configuration_wizards: function () {
            var self = this;
            new openerp.web.DataSet(this, 'res.config').call('start', [[]], function (action) {
                $.unblockUI();
                self.do_action(action, function () {
                    // TODO: less brutal reloading
                    window.location.reload(true);
                });
            });
        }
    });
};
