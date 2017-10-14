odoo.define('website.ace', function (require) {
'use strict';

var ajax = require('web.ajax');
var Widget = require('web.Widget');
var website = require('website.website');

var AceCommon = require('web_editor.ace');

var hash = "#advanced-view-editor";

var Ace = Widget.extend({
    events: {
        'click a[data-action=ace]': 'launchAce',
    },
    launchAce: function (e) {
        var self = this;
        if (!window.ace && !this.loadJS_def) {
            this.loadJS_def = ajax.loadJS('/web/static/lib/ace/ace.odoo-custom.js').then(function () {
                return $.when(ajax.loadJS('/web/static/lib/ace/mode-xml.js'),
                    ajax.loadJS('/web/static/lib/ace/theme-monokai.js'));
            });
        }

        if (e) {
            e.preventDefault();
        }

        return $.when(this.loadJS_def).then(function () {
            if (self.globalEditor) {
                self.globalEditor.open();
            } else {
                self.globalEditor = new ViewEditor(self);
                self.globalEditor.appendTo($(document.body));
            }
        });
    },
});

var ViewEditor = AceCommon.ViewEditor.extend({
    loadTemplates: function () {
        var self = this;
        var args = {
            key: $(document.documentElement).data('view-xmlid'),
            full: true,
            bundles: this.$('.js_include_bundles')[0].checked
        };
        return ajax
            .jsonRpc('/website/customize_template_get', 'call', args)
            .then(function (views) {
                self.loadViews.call(self, views);
                self.open.call(self);
                var curentHash = window.location.hash;
                var indexOfView = curentHash.indexOf("?view=");
                if (indexOfView >= 0) {
                    var viewId = parseInt(curentHash.substring(indexOfView + 6, curentHash.length), 10);
                    self.$('#ace-view-list').val(viewId).change();
                } else {
                    if (views.length >= 2) {
                        var mainTemplate = views[0];
                        self.$('#ace-view-list').val(mainTemplate.id).trigger('change');
                    }
                    window.location.hash = hash;
                }
            });
    },
    displayError: function () {
        var error = this._super.apply(this, arguments);
        website.error(error.title, error.message);
    },
    updateHash: function () {
        window.location.hash = hash + "?view=" + this.selectedViewId();
    },
    reloadPage: function () {
        this.updateHash();
        window.location.reload();
    },
    close: function () {
        window.location.hash = "";
        this.$el.removeClass('oe_ace_open').addClass('oe_ace_closed');
    },
});

website.TopBar.include({
    start: function () {
        this.ace = new Ace();
        return $.when(
            this._super.apply(this, arguments),
            this.ace.attachTo($('#html_editor'))
        );
    },
});

});
