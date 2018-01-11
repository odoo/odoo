(function () {
    'use strict';

    var website = openerp.website;
    website.add_template_file('/website/static/src/xml/website.xml');

    website.MobilePreview = openerp.Widget.extend({
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

    website.ready().done(function() {
        $(document.body).on('click', 'a[data-action=show-mobile-preview]', function() {
            new website.MobilePreview().appendTo($(document.body));
        });
    });

})();
