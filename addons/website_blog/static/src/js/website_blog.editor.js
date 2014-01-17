(function() {
    "use strict";

    var website = openerp.website;
    website.add_template_file('/website_blog/static/src/xml/website_blog.xml');

    website.is_editable = true;
    website.EditorBar.include({
        start: function() {
            var res = this._super();
            if ($("#wrap.js_blog").size()) {
                this.$("button[data-action=edit]").removeClass("hidden");
            }
            this.$(".dropdown:has(.oe_content_menu)").removeClass("hidden");
            return res;
        },
        events: _.extend({}, website.EditorBar.prototype.events, {
            'click a[data-action=new_blog_post]': function (ev) {
                ev.preventDefault();
                website.prompt({
                    window_title: "New Blog Post",
                    select: "Select Blog",
                    init: function (field) {
                        return website.session.model('blog.category')
                                .call('name_search', [], { context: website.get_context() });
                    },
                }).then(function (cat_id) {
                    document.location = '/blogpost/new?category_id=' + cat_id;
                });
            }
        }),
    });
})();
