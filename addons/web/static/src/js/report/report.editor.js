odoo.define('report.editor', function (require) {
'use strict';

require('web.dom_ready')
var core = require('web.core');
var utils = require('report.utils');
var editor = require('web_editor.editor');
var options = require('web_editor.snippets.options');

var web_base_url = $('html').attr('web-base-url');
var trusted_host = utils.get_host_from_url(web_base_url);
var trusted_protocol = utils.get_protocol_from_url(web_base_url);
var trusted_origin = utils.build_origin(trusted_protocol, trusted_host);

// Patch the editor's behavior when it is launched inside an iframe.
if (window.self !== window.top) {

    // And now we chain some deferred to `save` and `cancel` in order to inform
    // the report's client action that the actions are done.
    editor.Class.include({
        save: function () {
            // Force to not reload
            return this._super(false).then(function () {
                window.parent.postMessage('report.editor:save_ok', trusted_origin);
            });
        },
        cancel: function () {
            // Force to not reload
            return this._super(false).then(function () {
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

            switch (message) {
                case 'report.editor:ask_save':
                    core.bus.trigger('editor_save_request');
                    break;
                case 'report.editor:ask_discard':
                    core.bus.trigger('editor_discard_request');
                    break;
                default:
            }
        }
    }, false);
}

options.registry.many2one.include({
    _selectRecord: function ($li) {
        this._super.apply(this, arguments);
        if (this.$target.data('oe-field') !== 'partner_id') {
            return;
        }

        var $img = $('.header .row img:first');
        var css = window.getComputedStyle($img[0]);
        $img.css('max-height', css.height+'px');
        $img.attr('src', '/web/image/res.partner/' + this.ID + '/image');
        _.defer(function () {
            $img.removeClass('o_dirty');
        });
    }
});

});
