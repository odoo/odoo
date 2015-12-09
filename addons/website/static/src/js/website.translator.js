odoo.define('website.translator', function (require) {
'use strict';

var core = require('web.core');
var ajax = require('web.ajax');
var Widget = require('web.Widget');
var base = require('web_editor.base');
var translate = require('web_editor.translate');
var website = require('website.website');

var qweb = core.qweb;

if (!translate.translatable) {
    return;
}


website.TopBar.include({
    events: _.extend({}, website.TopBar.prototype.events, {
        'click [data-action="edit_master"]': 'edit_master',
        'click [data-action="translate"]': 'translate',
    }),
    translate: function (ev) {
        ev.preventDefault();
        if (translate.edit_translations) {
            translate.instance.edit();
        } else {
            location.search += '&edit_translations';
        }
    },
    edit_master: function (ev) {
        ev.preventDefault();
        var $link = $('.js_language_selector a[data-default-lang]');
        if (!$link.length) {
            // Fallback for old website
            var l = false;
            _.each($('.js_language_selector a'), function(a) {
               if (!l || a.href.length < l.href.length) { l = a; }
            });
            $link = $(l);
        }
        $link[0].search += ($link[0].search ? '&' : '?') + 'enable_editor=1';
        $link.click();
    },
});


if (!translate.edit_translations) {
    return;
}

ajax.loadXML('/website/static/src/xml/website.translator.xml', qweb);

var nodialog = 'website_translator_nodialog';

var Translate = translate.Class.include({
    onTranslateReady: function () {
        if(this.gengo_translate){
            this.translation_gengo_display();
        }
        this._super();
    },
    edit: function () {
        $("#oe_main_menu_navbar").hide();
        if (!localStorage[nodialog]) {
            var dialog = new TranslatorDialog();
            dialog.appendTo($(document.body));
            dialog.on('activate', this, function () {
                if (dialog.$('input[name=do_not_show]').prop('checked')) {
                    localStorage.removeItem(nodialog);
                } else {
                    localStorage.setItem(nodialog, true);
                }
                dialog.$el.modal('hide');
            });
        }
        return this._super();
    },
    cancel: function () {
        $("#oe_main_menu_navbar").show();
        return this._super();
    }
});

var TranslatorDialog = Widget.extend({
    events: _.extend({}, website.TopBar.prototype.events, {
        'hidden.bs.modal': 'destroy',
        'click button[data-action=activate]': function (ev) {
            this.trigger('activate');
        },
    }),
    template: 'website.TranslatorDialog',
    start: function () {
        this.$el.modal();
    },
});

});
