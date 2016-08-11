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
            if (blog_ids.length === 1) {
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
        // Destroy popOver and stop listening mouseup event on edit mode
        start: function () {
            $(".js_tweet, .js_comment").off('mouseup').trigger('mousedown');
            return this._super.apply(this, arguments);
        },
        saveElement: function ($el, context) {
            if ($el.is('.o_blog_cover_container')) {
                return ajax.jsonRpc("/blog/post_change_background", 'call', {
                    'post_id' : parseInt($el.closest("[name=\"blog_post\"], .website_blog").find("[data-oe-model=\"blog.post\"]").first().data("oe-id"), 10),
                    'cover_properties' : {
                        "background-image": $el.children(".o_blog_cover_image").css("background-image").replace(/"/g, ''),
                        "background-color": $el.data("filter_color"),
                        "opacity": $el.data("filter_value"),
                        "resize_class": $el.data("cover_class"),
                    }
                });
            }
            return this._super.apply(this, arguments);
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

    options.registry.blog_cover = options.Class.extend({
        init: function () {
            this._super.apply(this, arguments);

            this.$image = this.$target.children(".o_blog_cover_image");
            this.$filter = this.$target.children(".o_blog_cover_filter");
        },
        clear: function (type, value, $li) {
            if (type !== 'click') return;

            this.select_class(type, "", $());
            this.$image.css("background-image", "");
            this.$target.addClass("o_dirty");
        },
        change: function (type, value, $li) {
            if (type !== 'click') return;

            var $image = $("<img/>", {src: this.$image.css("background-image")});

            var editor = new widget.MediaDialog(null, {only_images: true}, $image, $image[0]).open();
            editor.on("saved", this, function (event, img) {
                var src = $image.attr("src");
                this.$image.css("background-image", src ? ("url(" + src + ")") : "");
                if (!this.$target.hasClass("cover")) {
                    var $li = this.$el.find("[data-select_class]").first();
                    this.select_class(type, $li.data("select_class"), $li);
                }
                this.set_active();
                this.$target.addClass("o_dirty");
            });
        },
        filter_value: function (type, value, $li) {
            this.$filter.css("opacity", value);
            this.$target.addClass('o_dirty');
        },
        filter_color: function (type, value, $li) {
            var $lis = this.$el.find("[data-filter_color]").addBack("[data-filter_color]");
            var classes = $lis.map(function () {return $(this).data("filter_color");}).get().join(" ");
            this.$filter.removeClass(classes);
            if (value) {
                this.$filter.addClass(value);
            }
            this.$target.addClass("o_dirty");
        },
        set_active: function () {
            this._super.apply(this, arguments);
            var self = this;

            this.$el.filter(":not([data-change])").toggleClass("hidden", !this.$target.hasClass("cover"));

            var $actives = this.$el.find('li[data-filter_value], li[data-filter_color]').removeClass("active")
                .filter(function () {
                    var data = $(this).data();
                    return (parseFloat(data.filter_value).toFixed(1) === parseFloat(self.$filter.css('opacity')).toFixed(1)
                        || self.$filter.hasClass(data.filter_color));
                }).addClass("active");

            this.$target.data("cover_class", this.$el.find(".active[data-select_class]").data("select_class") || "");
            this.$target.data("filter_value", $actives.filter("[data-filter_value]").data("filter_value") || 0.0);
            this.$target.data("filter_color", $actives.filter("[data-filter_color]").data("filter_color") || "");
        },
    });
});
