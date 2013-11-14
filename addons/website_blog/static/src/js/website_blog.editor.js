(function() {
    "use strict";

    var website = openerp.website;
    website.add_template_file('/website_blog/static/src/xml/website_blog.xml');

    website.EditorBar.include({
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
                    document.location = '/blog/' + cat_id + '/new';
                });
            }
        }),
    });
})();
