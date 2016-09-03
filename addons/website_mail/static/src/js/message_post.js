odoo.define('website_mail.thread', function(require) {
    'use strict';

    var web_editor_base = require('web_editor.base');
    var ajax = require('web.ajax');
    var core = require('web.core');
    var Widget = require('web.Widget');

    var qweb = core.qweb;
    
    // load qweb template
    ajax.loadXML('/website_mail/static/src/xml/chatter_message.xml', qweb);

    /**
     * Widget WebsiteMailThread
     *
     * Widget sending message to the server, using json request. Used to not refresh all
     * the page. Its DOM already exists on the page (The class of root element is
     * '.o_website_mail_thread').
     */
    var WebsiteMailThread = Widget.extend({
        events:{
            "click .o_website_chatter_json": "on_click",
        },
        on_click: function(e){
            var self = this;
            e.preventDefault();

            var $button = this.$(e.currentTarget);
            var $form = this.$('.o_website_chatter_form');
            var $error = this.$('.o_website_chatter_error');
            var action = $form.attr('action');
            var data = this._get_form_data($form);

            data.message = data.message.replace(/\n/g,"<br/>");
            if (data.message) {
                // make the 'send' button loading
                $button.attr('disabled', true);
                var button_bk = $button.html();
                $button.prepend('<i class="fa fa-refresh fa-spin"></i> ');
                // post message, shw/hide error message and empty textarea
                ajax.jsonRpc(action, 'call', data).then(function (result) {
                    if (result) {
                        $error.fadeOut();
                        self.prepend_message(result);
                        $form.find('textarea').val('');
                    } else {
                        $error.fadeIn();
                    }
                    $button.html(button_bk);
                    $button.attr('disabled', false);
                });
            }
        },
        prepend_message: function(message_data){
            var msg = qweb.render('website_mail.thread_message', message_data);
            var elem = $(msg).hide().prependTo(this.$('.o_website_comments'));
            elem.slideToggle();
            return elem;
        },
        _get_form_data: function($form){
            var unindexed_array = $form.serializeArray();
            var indexed_array = {};
            $.map(unindexed_array, function(n, i){
                indexed_array[n.name] = n.value;
            });
            return indexed_array;
        },
    });

    web_editor_base.ready().then(function(){
        if($('.o_website_mail_thread').length) {
            var mail_thread = new WebsiteMailThread($('body')).setElement($('.o_website_mail_thread'));
        }
    });

    return {
        WebsiteMailThread: WebsiteMailThread,
    }
});
