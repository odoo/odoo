odoo.define('website_blog.new_blog_post', function (require) {
"use strict";

var core = require('web.core');
var base = require('web_editor.base');
var Model = require('web.Model');
var website = require('website.website');
var contentMenu = require('website.contentMenu');

var _t = core._t;

contentMenu.TopBar.include({
    new_blog_post: function () {
        var model = new Model('blog.blog');
        model.call('name_search', [], { context: base.get_context() }).then(function (blog_ids) {
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

});

odoo.define('website_blog.editor', function (require) {
"use strict";

    var ajax = require('web.ajax');
    var widget = require('web_editor.widget');
    var options = require('web_editor.snippets.options');
    var rte = require('web_editor.rte');

    if(!$('.website_blog').length) {
        return $.Deferred().reject("DOM doesn't contain '.website_blog'");
    }

    rte.Class.include({
        saveElement: function ($el, context) {
            if ($el.is('#js_blogcover')) {
                return ajax.jsonRpc("/blog/post_change_background", 'call', {
                    'post_id' : +$('#blog_post_name').data('oe-id'),
                    'cover_properties' : {
                        "background-image": $el.css("background-image").replace(/"/g, ''),
                        "background-color": $el.attr("class"),
                        "opacity": $el.css("opacity"),
                        "resize_class": $('#title').attr('class'),
                    }
                });
            }
            return this._super($el, context);
        },
    });


    options.registry.many2one.include({
        select_record: function (li) {
            var self = this;
            this._super(li);
            if (this.$target.data('oe-field') === "author_id") {
                var $nodes = $('[data-oe-model="blog.post"][data-oe-id="'+this.$target.data('oe-id')+'"][data-oe-field="author_avatar"]');
                $nodes.each(function () {
                    var $img = $(this).find("img");
                    var css = window.getComputedStyle($img[0]);
                    $img.css({ width: css.width, height: css.height });
                    $img.attr("src", "/web_editor/image/res.partner/"+self.ID+"/image");
                });
                setTimeout(function () { $nodes.removeClass('o_dirty'); },0);
            }
        }
    });

    options.registry.website_blog = options.Class.extend({
        start : function(type, value, $li) {
            this._super();
            this.src = this.$target.css("background-image").replace(/url\(|\)|"|'/g,'').replace(/.*none$/,'');
            this.$image = $('<image src="'+this.src+'">');
        },
        clear : function(type, value, $li) {
            if (type !== 'click') return;
            this.src = null;
            this.$target.css({"background-image": '', 'min-height': $(window).height()});
            this.$image.removeAttr("src");
        },
        change : function(type, value, $li) {
            if (type !== 'click') return;
            var self = this;
            var editor  = new widget.MediaDialog(this.$image, this.$image[0], {only_images: true});
            editor.appendTo('body');
            editor.on('saved', self, function (event, img) {
                var url = self.$image.attr('src');
                self.$target.find('#js_blogcover').css({"background-image": url ? 'url(' + url + ')' : "", 'min-height': $(window).height()-$('#js_blogcover').offset().top});
                self.$target.find('#js_blogcover').addClass('o_dirty');
                self.buildingBlock.parent.rte_changed();
            });
        },
    });

});
