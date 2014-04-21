(function() {
    "use strict";

    var website = openerp.website;
    var _t = openerp._t;
    website.add_template_file('/website_doc/static/src/xml/website_doc.xml');

    website.is_editable = true;
    website.EditorBar.include({
        start: function() {
            website.is_editable_button = website.is_editable_button || !!$("#wrap").size();
            var res = this._super();
            this.$(".dropdown:has(.oe_content_menu)").removeClass("hidden");
            return res;
        },
        events: _.extend({}, website.EditorBar.prototype.events, {
            'click a[data-action=new_toc]': function (ev) {
                ev.preventDefault();
                website.prompt({
                    id: "editor_new_toc",
                    window_title: _t("New Table Of Content"),
                    input: "Table Of Content Name",
                }).then(function (toc_name) {
                    website.form('/doc/new', 'POST', {
                        toc_name: toc_name
                    });
                });
            }
        }),
    });
})();
