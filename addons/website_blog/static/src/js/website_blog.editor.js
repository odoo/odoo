odoo.define('website_blog.editor', function (require) {
"use strict";

var ajax = require('web.ajax');
var core = require('web.core');
var Model = require('web.Model');
var contentMenu = require('website.contentMenu');
var website_define = require('website.define');
var editor = require('website.editor');
var snippet_editor = require('website.snippets.editor');
var website = require('website.website');


var _t = core._t;

contentMenu.EditorBarContent.include({
    new_blog_post: function () {
        var model = new Model('blog.blog');
        model.call('name_search', [], { context: website.get_context() })
        .then(function (blog_ids) {
            if (blog_ids.length == 1) {
                document.location = '/blog/' + blog_ids[0][0] + '/post/new';
            } else if (blog_ids.length > 1) {
                website.prompt({
                    id: "editor_new_blog",
                    window_title: _t("New Blog Post"),
                    select: "Select Blog",
                    init: function (field) {
                        return blog_ids;
                    },
                }).then(function (blog_id) {
                    document.location = '/blog/' + blog_id + '/post/new';
                });
            }
        });
    },
});

website.if_dom_contains('.website_blog', function() {

    editor.EditorBar.include({
        edit: function () {
            $('.popover').remove();
            $('.cover_footer').off('click');
            this._super();
        },
        save : function () {
            var args = arguments;
            var super_call = this._super;
            var self = this;
            if ($('#js_blogcover').length) {
                var properties = {
                    "background-image": $('#js_blogcover').css("background-image").replace(/"/g, ''),
                    "background-color": $('#js_blogcover').attr("class"),
                    "opacity": $('#js_blogcover').css("opacity"),
                    "resize_class": $('#title').attr('class'),
                };
                ajax.jsonRpc("/blog/post_change_background", 'call', {
                    'post_id' : $('h1[data-oe-expression="blog_post.name"]').attr('data-oe-id'),
                    'cover_properties' : JSON.stringify(properties),
                }).always(function() {
                    super_call.apply(self, args);
                });
            } else {
                super_call.apply(self, args);
            }
        },
    });

    snippet_editor.options.many2one.include({
        select_record: function (li) {
            var self = this;
            this._super(li);
            if (this.$target.data('oe-field') === "author_id") {
                var $nodes = $('[data-oe-model="blog.post"][data-oe-id="'+this.$target.data('oe-id')+'"][data-oe-field="author_avatar"]');
                $nodes.each(function () {
                    var $img = $(this).find("img");
                    var css = window.getComputedStyle($img[0]);
                    $img.css({ width: css.width, height: css.height });
                    $img.attr("src", "/website/image/res.partner/"+self.ID+"/image");
                });
                setTimeout(function () { $nodes.removeClass('o_dirty'); },0);
            }
        }
    });

    snippet_editor.options.website_blog = snippet_editor.Option.extend({
        start : function(type, value, $li) {
            this._super();
            this.src = this.$target.css("background-image").replace(/url\(|\)|"|'/g,'').replace(/.*none$/,'');
            this.$image = $('<image src="'+this.src+'">');
        },
        clear : function(type, value, $li) {
            if (type !== 'click') return;
            this.src = null;
            this.$target.find('#js_blogcover').css({"background-image": '', "opacity": "1.0"}).attr("class", "oe_none");
            this.$target.attr("class", "");
            this.$image.removeAttr("src");
        },
        change : function(type, value, $li) {
            if (type !== 'click') return;
            var self = this;
            var _editor  = new editor.MediaDialog(this.$image, this.$image[0], {only_images: true});
            _editor.appendTo('body');
            _editor.on('saved', self, function (event, img) {
                var url = self.$image.attr('src');
                self.$target.find('#js_blogcover').css({"background-image": url ? 'url(' + url + ')' : ""});
                self.$target.attr("class","cover cover_full");
                this.$el.parent().find('.snippet-option-website_blog:not(li[data-change])').removeClass("hidden");
            });
        },
        cover_class : function(type, value, $li) {
            this.$target.attr("class", (type === 'over' || type === 'click') ? value : this.class);
        },
        opacity : function(type, value, $li) {
            this.$target.find('#js_blogcover').css("opacity", (type === 'over' || type === 'click') ? value : this.value);
        },
        bgcolor : function(type, value, $li) {
            this.$target.find('#js_blogcover').attr("class", (type === 'over' || type === 'click') ? value : this.background);
        },
        set_active: function(){
            this.background = this.$target.find('#js_blogcover').attr("class");
            this.class = this.$target.attr('class');
            this.value = this.$target.find('#js_blogcover').css('opacity');
            if ( this.$target.hasClass("cover") ) {
              this.$el.parent().find('.snippet-option-website_blog:not(li[data-change])').removeClass("hidden");
            } else {
                this.$el.parent().find('.snippet-option-website_blog:not(li[data-change])').addClass("hidden");
            }
            this.$el.find('li[data-bgcolor]').removeClass("active").siblings('[data-bgcolor="' + this.background + '"]').addClass("active");
            this.$el.find('li[data-opacity]').removeClass("active").siblings('[data-opacity="' + parseFloat(this.value).toFixed(1) + '"]').addClass("active");
            this.$el.find('li[data-cover_class]').removeClass("active").siblings('[data-cover_class="' + this.class + '"]').addClass("active");
        },
    });

});

});
