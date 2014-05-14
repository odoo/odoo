(function() {
    "use strict";

    var website = openerp.website;
    var _t = openerp._t;
    website.add_template_file('/website_blog/static/src/xml/website_blog.xml');

    website.is_editable = true;
    website.EditorBar.include({
        start: function() {
            website.is_editable_button = website.is_editable_button || !!$("#wrap.js_blog").size();
            var res = this._super();
            this.$(".dropdown:has(.oe_content_menu)").removeClass("hidden");
            return res;
        },
        events: _.extend({}, website.EditorBar.prototype.events, {
            'click a[data-action=new_blog_post]': function (ev) {
                ev.preventDefault();
                website.prompt({
                    id: "editor_new_blog",
                    window_title: _t("New Blog Post"),
                    select: "Select Blog",
                    init: function (field) {
                        return website.session.model('blog.blog')
                                .call('name_search', [], { context: website.get_context() });
                    },
                }).then(function (cat_id) {
                    document.location = '/blogpost/new?blog_id=' + cat_id;
                });
            },
        }),
        edit: function () {
            var self = this;
            $('.popover').remove();
            this._super();
            var vHeight = $(window).height();
            $('body').on('click','#change_cover',_.bind(this.change_bg, self.rte.editor, vHeight));
            $('body').on('click', '#clear_cover',_.bind(this.clean_bg, self.rte.editor, vHeight));
        },
        save : function() {
            var res = this._super();
            if ($('.cover').length) {
                openerp.jsonRpc("/blogpost/change_background", 'call', {
                    'post_id' : $('#blog_post_name').attr('data-oe-id'),
                    'image' : $('.cover').css('background-image').replace(/url\(|\)|"|'/g,''),
                });
            }
            return res;
        },
        clean_bg : function(vHeight) {
            $('.js_fullheight').css({"background-image":'none', 'min-height': vHeight});
        },
        change_bg : function(vHeight) {
            var self  = this;
            var element = new CKEDITOR.dom.element(self.element.find('.cover-storage').$[0]);
            var editor  = new website.editor.MediaDialog(self, element);
            $(document.body).on('media-saved', self, function (o) {
                var url = $('.cover-storage').attr('src');
                $('.js_fullheight').css({"background-image": !_.isUndefined(url) ? 'url(' + url + ')' : "", 'min-height': vHeight});
                $('.cover-storage').remove();
            });
            editor.appendTo('body');
        },
    });
})();
