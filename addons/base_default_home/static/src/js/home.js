openerp.base_default_home = function (openerp) {
    QWeb.add_template('/base_default_home/static/src/xml/base_default_home.xml');

    var old_home = openerp.base.WebClient.prototype.default_home;

    openerp.base_default_home = {
        applications: [[
                'sales',
                'purchases',
                'warehouse',
                'manufacturing'
            ], [
                'project',
                'accounting',
                'human resources',
                'marketing'
            ], [
                'knowledge',
                'point of sale',
                'tools',
                'administration'
            ]
        ]
    };

    openerp.base.WebClient.prototype.default_home = function () {
        var self = this;
        var Installer = new openerp.base.DataSet(
                this.session, 'base.setup.installer');
        Installer.call('already_installed', [], function (installed_modules) {
            if (!_(installed_modules).isEmpty()) {
                return old_home.call(self);
            }
            self.$element.find('.oe-application').html(
                QWeb.render('HomeInstallerTiles', {
                    rows: openerp.base_default_home.applications
            }));
        });
    }
};
