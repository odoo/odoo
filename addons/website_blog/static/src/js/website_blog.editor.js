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
            $('.popover').remove();
            this._super();
            var vHeight = $(window).height();
            $('body').on('click','#change_cover',_.bind(this.change_bg,{},vHeight));
            $('body').on('click', '#clear_cover',_.bind(this.clean_bg,{},vHeight));
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
            var editor  = new  website.editor.ImageDialog();
            editor.on('start', self, function (o) {
                o.url = $('.js_fullheight').length ? $('.js_fullheight').css('background-image').replace(/url\(|\)|"|'/g,'') : ''; 
            });
            editor.on('save', self, function (o) {
                $('.js_fullheight').css({"background-image": o.url && o.url !== "" ? 'url(' + o.url + ')' : "", 'min-height': vHeight})
            });
            editor.appendTo('body');
        },
    });
})();
