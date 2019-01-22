odoo.define('website.website_modal', function (require) {
'use strict';

    require('web.dom_ready');

    $('body').on('shown.bs.modal', function (e) {
        $(e.target).addClass('modal_shown');
    });
});
