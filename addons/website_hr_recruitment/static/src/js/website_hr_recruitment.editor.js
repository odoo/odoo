(function() {
    "use strict";
    var website = openerp.website;
    website.add_template_file('/website_hr_recruitment/static/src/xml/website_hr_recruitment.xml');

    website.is_editable = true;
    website.EditorBar.include({
        start: function() {
            var res = this._super();
            if ($("#wrap.js_hr_recruitment").size()) {
                this.$("button[data-action=edit]").removeClass("hidden");
            }
            this.$(".dropdown:has(.oe_content_menu)").removeClass("hidden");
            return res;
        },
    });
})();
