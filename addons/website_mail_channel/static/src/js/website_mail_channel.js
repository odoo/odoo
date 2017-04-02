odoo.define('website_mail_channel', function (require) {
"use strict";

var ajax = require('web.ajax');

$(document).ready(function () {

    $('.o_mg_link_hide').on('click', function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        var $container = $link.parents('div').first();
        $container.find('.o_mg_link_hide').first().hide();
        $container.find('.o_mg_link_show').first().show();
        $container.find('.o_mg_link_content').first().show();
        return false;
    });

    $('.o_mg_link_show').on('click', function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        var $container = $link.parents('div').first();
        $container.find('.o_mg_link_hide').first().show();
        $container.find('.o_mg_link_show').first().hide();
        $container.find('.o_mg_link_content').first().hide();
        return false;
    });

    $('body').on('click', 'button.o_mg_read_more', function (ev) {
        var $link = $(ev.target);
        return ajax.jsonRpc($link.data('href'), 'call', {
            'last_displayed_id': $link.data('msg-id'),
        }).then(function (data) {
            if (! data) {
                return true;
            }
            var $thread_container = $link.parents('.o_mg_replies').first().find('ul.media-list');
            if ($thread_container) {
                var $last_msg = $thread_container.find('li.media').last();
                $(data).find('li.media').insertAfter($last_msg);
                $(data).find('p.well').appendTo($thread_container);
            }
            var $show_more = $link.parents('p.well').first();
            $show_more.remove();
            return true;
        });
    });
});

});
