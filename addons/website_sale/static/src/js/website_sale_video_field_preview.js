odoo.define('website_sale.video_field_preview', function (require) {
"use strict";


var AbstractField = require('web.AbstractField');
var core = require('web.core');
var fieldRegistry = require('web.field_registry');

var QWeb = core.qweb;

/**
 * Displays preview of the video showcasing product.
 */
var FieldVideoPreview = AbstractField.extend({
    className: 'd-block o_field_video_preview',

    _render: function () {
        this.$el.html(QWeb.render('productVideo', {
            embedCode: this.value,
        }));
    },
});

fieldRegistry.add('video_preview', FieldVideoPreview);

return FieldVideoPreview;

});
