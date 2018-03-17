odoo.define('app_odoo_customize.switch_language', function (require) {
    "use strict";

    var Model = require('web.Model');
    var session = require('web.session');
    var UserMenu = require('web.UserMenu');

    UserMenu.include({
        on_menu_lang: function (ev) {
            var self = this;
            var lang = ($(ev).data("lang-id"));
            new Model('res.users').call('write', [[session.uid], {'lang': lang}]).then(function () {
                self.do_action({
                    type: 'ir.actions.client',
                    res_model: 'res.users',
                    tag: 'reload_context',
                    target: 'current'
                });
            });
            return false;
        },
    });
    //
    $(document).ready(function () {
        var self = this;
        var lang_list = '';
        setTimeout(function () {
            new Model('ir.config_parameter').call('search_read', [[['key', '=', 'app_show_lang']], ['value']]).then(function (show) {
                if (show.length >= 1 && (show[0]['value'] == "False"))
                    $('switch-lang').hide();
                else {
                    new Model('res.lang').call('search_read', [[], ['name', 'code']]).then(function (res) {
                        _.each(res, function (lang) {
                            var a = '';
                            if (lang['code'] === session.user_context.lang) {
                                a = '<i class="fa fa-check"></i>';
                            } else {
                                a = '';
                            }
                            lang_list += '<li><a href="#" data-menu="lang" data-lang-id="' + lang['code'] + '"><img class="flag" src="app_odoo_customize/static/src/img/flags/' + lang['code'] + '.png"/>' + lang['name'] + a + '</a></li>';
                        });
                        lang_list += '<li class="divider"></li>';
                        $('switch-lang').replaceWith(lang_list);
                    });
                }
            });
        }, 2500);
    });
});
