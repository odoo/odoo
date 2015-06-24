odoo.define('website_portal', function(require) {
    'use strict';

    var website = require('website.website');
    var qweb = require('qweb');
    website.ready().done(function() {

        $('.oe_website_portal').on('change', "select[name='country_id']", function () {
            var $select = $("select[name='state_id']");
            $select.find("option:not(:first)").hide();
            var nb = $select.find("option[data-country_id="+($(this).val() || 0)+"]").show().size();
            $select.parent().toggle(nb>1);
        });
        $('.oe_website_portal').find("select[name='country_id']").change();

        $('.wp_show_more').on('click', function(ev) {
            ev.preventDefault();
            $(this).parents('table').find(".to_hide").toggleClass('hidden');
            $(this).find('span').toggleClass('hidden');
        });

    });

});
