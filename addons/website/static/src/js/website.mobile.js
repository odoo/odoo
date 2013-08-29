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
            'hidden': 'close'
        },
        start: function () {
            $(document.body).addClass('oe_stop_scrolling');
            document.getElementById("mobile-viewport").src = window.location.href + "?mobile-preview=true";
            this.$el.modal();
        },
        close: function () {
            $(document.body).removeClass('oe_stop_scrolling');
            this.destroy();
        },
    });
})();
