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
            if ($el.is('.website_blog #title')) {
                return ajax.jsonRpc("/blog/post_change_background", 'call', {
                    'post_id' : +$el.find('#blog_post_name').data('oe-id'),
                    'cover_properties' : {
                        "background-image": $el.find('#js_blogcover').css("background-image").replace(/"/g, ''),
                        "background-color": $el.find('#js_blogcover').attr("class"),
                        "opacity": $el.find('#js_blogcover').css("opacity"),
                        "resize_class": $el.attr('class'),
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
                    $img.attr("src", "/web/image/res.partner/"+self.ID+"/image");
                });
                setTimeout(function () { $nodes.removeClass('o_dirty'); },0);
            }
        }
    });

    options.registry.website_blog = options.Class.extend({
        start : function() {
            this.$cover = this.$target.find('#js_blogcover');
            this.src = this.$target.css("background-image").replace(/url\(|\)|"|'/g,'').replace(/.*none$/,'');
            this.$image = $('<image src="'+this.src+'">');
            this._super();
        },
        clear : function(type, value, $li) {
            if (type !== 'click') return;
            this.src = null;
            this.$cover.css({"background-image": '', 'min-height': ''});
            this.$image.removeAttr("src");
            this.$target.removeClass('cover cover_full cover_narrow');
        },
        change : function(type, value, $li) {
            if (type !== 'click') return;
            var self = this;
            var editor  = new widget.MediaDialog(this.$image, this.$image[0], {only_images: true});
            editor.appendTo('body');
            editor.on('saved', self, function (event, img) {
                var url = self.$image.attr('src');
                self.$cover.css({"background-image": url ? 'url(' + url + ')' : "", 'min-height': $(window).height()-this.$cover.offset().top});
                self.$target.addClass('o_dirty cover cover_full');
                self.set_active();
            });
        },
        cover_class : function(type, value, $li) {
            this.$target.attr("class", (type === 'over' || type === 'click') ? value : this.class);
            this.$target.addClass('o_dirty');
        },
        opacity : function(type, value, $li) {
            this.$cover.css("opacity", (type === 'over' || type === 'click') ? value : this.value);
            this.$target.addClass('o_dirty');
        },
        bgcolor : function(type, value, $li) {
            this.$cover.attr("class", (type === 'over' || type === 'click') ? value : this.background);
            this.$target.addClass('o_dirty');
        },
        set_active: function(){
            this._super();
            this.background = this.$cover.attr("class");
            this.class = this.$target.attr('class');
            this.value = this.$cover.css('opacity');
            this.$el.parent().find('.snippet-option-website_blog:not(li[data-change])').toggleClass("hidden", !this.$target.hasClass("cover"));
            this.$el.find('li[data-bgcolor], li[data-opacity], li[data-cover_class]').removeClass("active");
            this.$el.find('[data-bgcolor="' + this.background + '"], [data-opacity="' + parseFloat(this.value).toFixed(1) + '"], [data-cover_class*="' + ((this.class||'').indexOf('cover_full') === -1 ? 'container' : 'cover_full') + '"]').addClass("active");
        },
    });

});
