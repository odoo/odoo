odoo.define('mail.announcement', function (require) {
"use strict";

var core = require('web.core');
var Model = require('web.DataModel');
var session = require('web.session');
var WebClient = require('web.WebClient');

var QWeb = core.qweb;

WebClient.include({
    show_application: function() {
        return $.when(this._super.apply(this, arguments)).then(this.proxy('show_announcement_bar'));
    },
    _ab_location: function(dbuuid) {
        return _.str.sprintf('https://services.openerp.com/openerp-enterprise/ab/css/%s.css', dbuuid);
    },
    show_announcement_bar: function() {
        if (session.get_cookie('ab') === 'c') {
            return;
        }
        var self = this;
        var config_parameter = new Model('ir.config_parameter');
        $(QWeb.render('WebClient.announcement_bar')).prependTo($('body'));
        var $bar = $('#announcement_bar_table');

        return config_parameter.call('get_param', ['database.uuid', false]).then(function(dbuuid) {
            if (!dbuuid) {
                return;
            }
            var $link = $bar.find('.url a');
            $link.attr('href', _.str.sprintf('%s/%s', $link.attr('href'), dbuuid));
            var $css = $('<link />').attr({
                rel : 'stylesheet',
                type: 'text/css',
                media: 'screen',
                href: self._ab_location(dbuuid)
            });
            $css.on('load', function() {
                var close = function() {
                    var ttl = 7*24*60*60;
                    session.set_cookie('ab', 'c', ttl);
                    $bar.slideUp();
                    setTimeout(function () {
                        $('.openerp_webclient_container').css('height', 'calc(100% - 34px)');                            
                    }, 400);
                };
                /*
                    We need a timeout of at least 350ms because the announcement bar appears
                    with an animation of 350ms and the computed height might be wrong if we don't wait
                */
                setTimeout(function(){
                    var height = $('#announcement_bar_table').outerHeight() 
                                + $('#oe_main_menu_navbar').outerHeight();
                    $('.openerp_webclient_container').css('height', 'calc(100% - ' + height + 'px)');
                    $bar.find('.close').on('click', close);
                    self.trigger('ab_loaded', $bar);
                }, 400);
            });

            $('head').append($css);
        }).fail(function(result, ev){
            ev.preventDefault();
        });
    }
});

});
