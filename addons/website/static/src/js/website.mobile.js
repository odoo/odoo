(function () {
    'use strict';

    var website = openerp.website;
    website.EditorBar.include({
        events: _.extend({}, website.EditorBar.prototype.events, {
            'click a[data-action=show-mobile-preview]': 'mobilePreview',
        }),
        mobilePreview: function () {
            (new website.MobilePreview()).appendTo($(document.body));
        },
    });

    website.MobilePreview = openerp.Widget.extend({
        template: 'website.mobile_preview',
        events: {
            'hidden': 'destroy'
        },
        start: function () {
            document.getElementById("mobile-viewport").src = window.location.href + "?mobile-preview=true";
            this.$el.modal();
        },
    });
})();
