(function() {
    "use strict";
    var website = openerp.website;
    website.add_template_file('/website_hr_recruitment/static/src/xml/website_hr_recruitment.xml');

    website.EditorBar.include({
        start: function() {
            website.is_editable_button = website.is_editable_button || !!$("#wrap.js_hr_recruitment").size();
            var res = this._super();
            this.$(".dropdown:has(.oe_content_menu)").removeClass("hidden");
            return res;
        },
    });
})();
