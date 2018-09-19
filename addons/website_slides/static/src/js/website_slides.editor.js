odoo.define('website_slides.editor', function (require) {
"use strict";

var core = require('web.core');
var Dialog = require('web.Dialog');
var QWeb = core.qweb;
var WebsiteNewMenu = require("website.newMenu");

var _t = core._t;

WebsiteNewMenu.include({
    actions: _.extend({}, WebsiteNewMenu.prototype.actions || {}, {
        new_slide: '_createNewSlide',
    }),
    xmlDependencies: WebsiteNewMenu.prototype.xmlDependencies.concat(
        ['/website_slides/static/src/xml/website_slides.xml']
    ),
    _createNewSlide: function () {
        var self = this;
        self._rpc({
            route: '/slides/channels',
        }).then(function (data) {
            new Dialog(self, {
                title: _t("New slide"),
                subtitle: _t("On which channel do you want to add a slide?"),
                size: 'medium',
                $content: QWeb.render('website.slide.create', data),
                buttons: [{
                    text: _t('Select'),
                    classes: 'btn-primary',
                    click: function () {
                        var channel_id = this.$("option:selected").val();
                        if (channel_id) {
                            window.location.href = '/slides/' + channel_id + '?enable_slide_upload';
                        }
                    }
                }, {
                    text: _t('Cancel'), close: true
                },]
            }).open();
        });
    },
});
});
