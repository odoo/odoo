odoo.define('website.iframe_widget', function (require) {
"use strict";


var AbstractField = require('web.AbstractField');
var core = require('web.core');
var fieldRegistry = require('web.field_registry');

var QWeb = core.qweb;

/**
 * Display iframe
 */
var FieldIframePreview = AbstractField.extend({
    className: 'd-block o_field_iframe_preview m-0 h-100',

    _render: function () {
        this.$el.html(QWeb.render('website.iframeWidget', {
            url: this.value,
        }));
    },
});

fieldRegistry.add('iframe', FieldIframePreview);

return FieldIframePreview;

});
