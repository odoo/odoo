odoo.define('website_mail_post', function(require) {
    'use strict';
    require('website.website');
    var qweb = require('qweb');
    var ajax = require('web.ajax');
    ajax.loadXML('/website_mail/static/src/xml/chatter_message.xml', qweb);

    if(!$('.o_website_chatter_json').length) {
        return $.Deferred().reject("DOM doesn't contain '.o_website_chatter_json'");
    }

    $('.o_website_chatter_json').on('click', function(ev) {
        ev.preventDefault();
        var $button = $(this);
        var $form = $(this).parents().find('.o_website_chatter_form');
        var action = $form.attr('action');
        var data = getFormData($form);
        data.message = data.message.replace(/\n/g,"<br/>");
        if (data.message) {
            $button.attr('disabled', true);
            var button_bk = $button.html();
            $button.prepend('<i class="fa fa-refresh fa-spin"></i> ');
            ajax.jsonRpc(action, 'call', data).then(function (result) {
                if (result) {
                    $('.o_website_chatter_error').fadeOut();
                    var msg = qweb.render('website_mail.thread_message', result);
                    var elem = $(msg).hide().prependTo($('.o_website_comments'));
                    elem.slideToggle();
                    $form.find('textarea').val('');
                } else {
                    $('o_website_chatter_error').fadeIn();
                }
                $button.html(button_bk);
                $button.attr('disabled', false);
            });
        }

        function getFormData($form){
            var unindexed_array = $form.serializeArray();
            var indexed_array = {};

            $.map(unindexed_array, function(n, i){
                indexed_array[n.name] = n.value;
            });

            return indexed_array;
        }
    });
});
