$(document).ready(function() {
    "use strict";

    var website = openerp.website;
    var _t = openerp._t;

    website.EditorBarContent.include({
        new_blog_post: function() {
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
    });
    if ($('.website_blog').length) {
        website.EditorBar.include({
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
                    $('.cover-storage').hide();
                });
                editor.appendTo('body');
            },
        });
    }
});
