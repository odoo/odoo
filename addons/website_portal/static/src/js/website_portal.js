(function () {
    'use strict';

    var website = openerp.website;
    var qweb = openerp.qweb;
    website.ready().done(function() {

        $('.oe_website_portal').on('change', "select[name='country_id']", function () {
            var $select = $("select[name='state_id']");
            $select.find("option:not(:first)").hide();
            var nb = $select.find("option[data-country_id="+($(this).val() || 0)+"]").show().size();
            $select.parent().toggle(nb>1);
        });
        $('.oe_website_portal').find("select[name='country_id']").change();
        
    });

})();