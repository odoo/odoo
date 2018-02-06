odoo.define('website.content.lazy_template_call', function (require) {
'use strict';

var Widget = require('web.Widget');
var websiteRootData = require('website.WebsiteRoot');

var LazyTemplateRenderer = Widget.extend({
    /**
     * Lazy replaces the `[data-oe-call]` elements by their corresponding
     * template content.
     *
     * @override
     */
    start: function () {
        var $oeCalls = this.$('[data-oe-call]');
        var oeCalls = _.uniq($oeCalls.map(function () {
            return $(this).data('oe-call');
        }).get());
        if (!oeCalls.length) {
            return $.when(this._super.apply(this, arguments));
        }

        var def = this._rpc({
            route: '/website/multi_render',
            params: {
                ids_or_xml_ids: oeCalls,
            },
        }).then(function (data) {
            _.each(data, function (d, k) {
                var $data = $(d).addClass('o_block_' + k);
                $oeCalls.filter('[data-oe-call="' + k + '"]').each(function () {
                    $(this).replaceWith($data.clone());
                });
            });
        });

        return $.when(this._super.apply(this, arguments), def);
    },
});

websiteRootData.websiteRootRegistry.add(LazyTemplateRenderer, '#wrapwrap');

return LazyTemplateRenderer;
});
