
odoo.define('website_portal', function(require) {
    'use strict';
    require('website.website');

    if(!$('.o_website_portal').length) {
        return $.Deferred().reject("DOM doesn't contain '.o_website_portal'");
    }

    if ($('.o_website_portal_details').length) {
        var state_options = $("select[name='state_id']:enabled option:not(:first)");
        $('.o_website_portal_details').on('change', "select[name='country_id']", function () {
            var select = $("select[name='state_id']");
            state_options.detach();
            var displayed_state = state_options.filter("[data-country_id="+($(this).val() || 0)+"]");
            var nb = displayed_state.appendTo(select).show().size();
            select.parent().toggle(nb>=1);
        });
        $('.o_website_portal_details').find("select[name='country_id']").change();
    }

    if ($('.o_portal_search_panel').length) {
        $('.o_portal_search_panel .search-submit').click(function() {
            var search = $.deparam(window.location.search.substring(1));
            search.search_in = $(".o_portal_search_panel li.active a").attr("href").replace("#","");
            search.search = $(".o_portal_search_panel input[name='search']").val();
            window.location.search = $.param(search);
        });

        $('.o_portal_search_panel .dropdown-menu').find('a').click(function(e) {
            e.preventDefault();
            $(this).parents('.dropdown-menu').find('li').removeClass('active');
            $(this).parent('li').addClass('active');
            var label = $(this).clone();
            label.find('span.nolabel').remove();
            $(".o_portal_search_panel span#search_label").text(label.text());
        });
        // init search label
        $('.o_portal_search_panel .dropdown-menu').find('li.active a').trigger('click');

        $(".o_portal_search_panel input[name='search']").on('keyup', function (e) {
            if (e.keyCode === 13) {
               $('.o_portal_search_panel .search-submit').trigger('click');
            }
        });
    }
});
