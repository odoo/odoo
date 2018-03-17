odoo.define('app_odoo_customize.customize_user_menu', function (require) {
    "use strict";
    var Model = require('web.Model');
    var session = require('web.session');

    var UserMenu = require('web.UserMenu');
    var documentation_url;
    var documentation_dev_url;
    var support_url;
    var account_title;
    var account_url;
    UserMenu.include({
        on_menu_debug: function () {
            window.location = $.param.querystring(window.location.href, 'debug');
        },
        on_menu_debugassets: function () {
            window.location = $.param.querystring(window.location.href, 'debug=assets');
        },
        on_menu_quitdebug: function () {
            window.location.search = "?";
        },
        on_menu_documentation: function () {
            window.open(documentation_url, '_blank');
        },
        on_menu_documentation_dev: function () {
            window.open(documentation_dev_url, '_blank');
        },
        on_menu_support: function () {
            window.open(support_url, '_blank');
        },
        on_menu_account: function () {
            window.open(account_url, '_blank');
        },
    });

    $(document).ready(function () {
        var self = this;
        documentation_url = 'http://www.sunpop.cn/documentation/user/10.0/zh_CN/index.html';
        documentation_dev_url = 'http://www.sunpop.cn/documentation/10.0/index.html';
        support_url = 'http://www.sunpop.cn/trial';
        account_title = 'My Online Account';
        account_url = 'http://www.sunpop.cn/my-account';
        setTimeout(function () {
            new Model('ir.config_parameter').call('search_read', [[['key', '=', 'app_show_debug']], ['value']]).then(function (show) {
                if (show.length >= 1 && (show[0]['value'] == "False")) {
                    $('[data-menu="debug"]').parent().hide();
                    $('[data-menu="debugassets"]').parent().hide();
                    $('[data-menu="quitdebug"]').parent().hide();
                }
            });
            new Model('ir.config_parameter').call('search_read', [[['key', '=', 'app_show_documentation']], ['value']]).then(function (show) {
                if (show.length >= 1 && (show[0]['value'] == "False"))
                    $('[data-menu="documentation"]').parent().hide();
                else {
                    new Model('ir.config_parameter').call('search_read', [[['key', '=', 'app_documentation_url']], ['value']]).then(function (res) {
                        if (res.length >= 1) {
                            _.each(res, function (item) {
                                documentation_url = item['value'];
                            });
                        }
                    });
                }
            });
            new Model('ir.config_parameter').call('search_read', [[['key', '=', 'app_show_documentation_dev']], ['value']]).then(function (show) {
                if (show.length >= 1 && (show[0]['value'] == "False"))
                    $('[data-menu="documentation_dev"]').parent().hide();
                else {
                    new Model('ir.config_parameter').call('search_read', [[['key', '=', 'app_documentation_dev_url']], ['value']]).then(function (res) {
                        if (res.length >= 1) {
                            _.each(res, function (item) {
                                documentation_dev_url = item['value'];
                            });
                        }
                    });
                }
            });
            new Model('ir.config_parameter').call('search_read', [[['key', '=', 'app_show_support']], ['value']]).then(function (show) {
                if (show.length >= 1 && (show[0]['value'] == "False"))
                    $('[data-menu="support"]').parent().hide();
                else {
                    new Model('ir.config_parameter').call('search_read', [[['key', '=', 'app_support_url']], ['value']]).then(function (res) {
                        if (res.length >= 1) {
                            _.each(res, function (item) {
                                support_url = item['value'];
                            });
                        }
                    });
                }
            });
            new Model('ir.config_parameter').call('search_read', [[['key', '=', 'app_show_account']], ['value']]).then(function (show) {
                if (show.length >= 1 && (show[0]['value'] == "False"))
                    $('[data-menu="account"]').parent().hide();
                else {
                    new Model('ir.config_parameter').call('search_read', [[['key', '=', 'app_account_title']], ['value']]).then(function (res) {
                        if (res.length >= 1) {
                            _.each(res, function (item) {
                                account_title = item['value'];
                            });
                        }
                        $('[data-menu="account"]').html(account_title);
                    });
                }
            });
            new Model('ir.config_parameter').call('search_read', [[['key', '=', 'app_account_url']], ['value']]).then(function (res) {
                if (res.length >= 1) {
                    _.each(res, function (item) {
                        account_url = item['value'];
                    });
                }
            });
            new Model('ir.config_parameter').call('search_read', [[['key', '=', 'app_show_poweredby']], ['value']]).then(function (show) {
                if (show.length >= 1 && (show[0]['value'] == "False"))
                    $('.o_sub_menu_footer').hide();
            });
        }, 2500);
    });
})
