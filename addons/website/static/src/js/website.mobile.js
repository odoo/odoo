odoo.define('website.mobile', function (require) {
'use strict';

var core = require('web.core');
var ajax = require('web.ajax');
var Widget = require('web.Widget');
var base = require('web_editor.base');
var website = require('website.website');

var qweb = core.qweb;

var MobilePreview = Widget.extend({
    template: 'website.mobile_preview',
    events: {
        'hidden.bs.modal': 'destroy'
    },
    start: function() {
        if (!window.location.origin) { // fix for ie9
            window.location.origin = window.location.protocol + "//" + window.location.hostname + (window.location.port ? ':' + window.location.port: '');
        }
        document.getElementById("mobile-viewport").src = window.location.origin + window.location.pathname + window.location.search + "#mobile-preview";
        this.$el.modal();
    },
    destroy: function() {
        $('.modal-backdrop').remove();
        this._super();
    },
});

website.TopBar.include({
    start: function () {
        this.$el.on('click', 'a[data-action=show-mobile-preview]', function() {
            new MobilePreview().appendTo($(document.body));
        });
        return this._super();
    }
});

});
