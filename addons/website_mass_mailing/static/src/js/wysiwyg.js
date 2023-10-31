odoo.define('website_mass_mailing.wysiwyg', function (require) {
'use strict';

const Wysiwyg = require('web_editor.wysiwyg');

Wysiwyg.include({
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _saveElement: function ($el, context, withLang) {
        var self = this;
        var defs = [this._super.apply(this, arguments)];
        var $popups = $el.find('.o_newsletter_popup');
        _.each($popups, function (popup) {
            var $popup = $(popup);
            var content = $popup.data('content');
            if (content) {
                defs.push(self._rpc({
                    route: '/website_mass_mailing/set_content',
                    params: {
                        'newsletter_id': parseInt($popup.attr('data-list-id')),
                        'content': content,
                    },
                }));
            }
        });
        return Promise.all(defs);
    },
});

});
