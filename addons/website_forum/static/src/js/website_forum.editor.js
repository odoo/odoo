(function() {
    "use strict";

    var website = openerp.website;
    var _t = openerp._t;
    website.add_template_file('/website_forum/static/src/xml/website_forum.xml');

    website.is_editable = true;
    website.EditorBar.include({
        start: function() {
            website.is_editable_button = website.is_editable_button || !!$("#wrap").size();
            var res = this._super();
            this.$(".dropdown:has(.oe_content_menu)").removeClass("hidden");
            return res;
        },
        events: _.extend({}, website.EditorBar.prototype.events, {
            'click a[data-action=new_question]': function (ev) {
                ev.preventDefault();
                website.prompt({
                    id: "editor_new_forum",
                    window_title: _t("New Forum"),
                    input: "Forum Name",
                }).then(function (forum_name) {
                    website.form('/forum/new', 'POST', {
                        forum_name: forum_name
                    });
                });
            }
        }),
    });
})();
