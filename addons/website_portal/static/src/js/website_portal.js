odoo.define('website_portal', function(require) {
    'use strict';
    require('website.website');

    if(!$('.o_website_portal_details, .o_my_show_more').length) {
        return $.Deferred().reject("DOM doesn't contain '.o_website_portal_details' or '.o_my_show_more'");
    }

    var state_options = $("select[name='state_id']:enabled option:not(:first)");
    $('.o_website_portal_details').on('change', "select[name='country_id']", function () {
        var select = $("select[name='state_id']");
        state_options.detach();
        var displayed_state = state_options.filter("[data-country_id="+($(this).val() || 0)+"]");
        var nb = displayed_state.appendTo(select).show().size();
        select.parent().toggle(nb>=1);
    });
    $('.o_website_portal_details').find("select[name='country_id']").change();

    $('.o_my_show_more').on('click', function(ev) {
        ev.preventDefault();
        $(this).parents('table').find(".to_hide").toggleClass('hidden');
        $(this).find('span').toggleClass('hidden');
    });
});
