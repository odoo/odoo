odoo.define('report.editor', function (require) {
'use strict';

var ajax = require('web.ajax');
var core = require('web.core');
var utils = require('report.utils');
var editor = require('web_editor.editor');
var options = require('web_editor.snippets.options');

var web_base_url = $('html').attr('web-base-url');
var trusted_host = utils.get_host_from_url(web_base_url);
var trusted_protocol = utils.get_protocol_from_url(web_base_url);
var trusted_origin = utils.build_origin(trusted_protocol, trusted_host);

ajax.loadXML('/web/static/src/xml/base_common.xml', core.qweb);

// Patch the editor's behavior when it is launched inside an iframe.
if (window.self !== window.top) {
    $(document.body).addClass('o_in_iframe'); //  in order to apply css rules

    // As `reload` is called after `save` and `cancel`, we nullify this function
    // if the editor in order to be able to chain some deferred to `save` and
    // `cancel`.
    editor.reload = function () {
        return $.when();
    };

    // And now we chain some deferred to `save` and `cancel` in order to inform
    // the report's client action that the actions are done.
    editor.Class.include({
        save: function () {
            return this._super.apply(this, arguments).then(function () {
                window.parent.postMessage('report.editor:save_ok', trusted_origin);
            });
        },
        cancel: function () {
            return this._super.apply(this, arguments).then(function () {
                window.parent.postMessage('report.editor:discard_ok', trusted_origin);
            });
        },
    });

    // postMessage logic.
    var AUTHORIZED_MESSAGES = [
        'report.editor:ask_discard',
        'report.editor:ask_save',
    ];

    window.addEventListener('message', function (ev) {
        // Check the origin of the received message.
        var message_origin = utils.build_origin(ev.source.location.protocol, ev.source.location.host);
        if (message_origin === trusted_origin) {
            // Check the syntax of the received message.
            var message = ev.data;
            if (! _.isString(message) || (_.isString(message) && ! _.contains(AUTHORIZED_MESSAGES, message))) {
                return;
            }

            switch(message) {
                case 'report.editor:ask_save':
                    editor.editor_bar.save();
                    break;
                case 'report.editor:ask_discard':
                    editor.editor_bar.cancel();
                    break;
                default:
            }
        }
    }, false);

    // Allow to send commands to the webclient when the editor is disabled.
    if (window.location.search.indexOf('enable_editor') === -1) {
        // `do_action` command
        $('[res-id][res-model][view-type]')
            .wrap('<a/>')
                .attr('href', '#')
            .on('click', function (ev) {
                ev.preventDefault();
                var action = {
                    'type': 'ir.actions.act_window',
                    'view_type': $(this).attr('view-type'),
                    'view_mode': $(this).attr('view-mode') || $(this).attr('view-type'),
                    'res_id': Number($(this).attr('res-id')),
                    'res_model': $(this).attr('res-model'),
                    'views': [[$(this).attr('view-id') || false, $(this).attr('view-type')]],
                };
                window.parent.postMessage({
                    'message': 'report:do_action',
                    'action': action,
                }, trusted_origin);
            });
    }
}

options.registry.many2one.include({
    select_record: function (li) {
        var self = this;
        this._super(li);
        if (this.$target.data('oe-field') === "partner_id") {
            var $img = $('.header .row img:first');
            var css = window.getComputedStyle($img[0]);
            $img.css("max-height", css.height+'px');
            $img.attr("src", "/web/image/res.partner/"+self.ID+"/image");
            setTimeout(function () { $img.removeClass('o_dirty'); },0);
        }
    }
});

});
