odoo.define('website_blog.new_blog_post', function (require) {
'use strict';

var core = require('web.core');
var weContext = require('web_editor.context');
var wUtils = require('website.utils');
var WebsiteNewMenu = require('website.newMenu');

var _t = core._t;

WebsiteNewMenu.include({
    actions: _.extend({}, WebsiteNewMenu.prototype.actions || {}, {
        new_blog_post: '_createNewBlogPost',
    }),

    //----------------------------------------------------------------------
    // Actions
    //----------------------------------------------------------------------

    /**
     * Asks the user information about a new blog post to create, then creates
     * it and redirects the user to this new page.
     *
     * @private
     */
    _createNewBlogPost: function () {
        return this._rpc({
            model: 'blog.blog',
            method: 'name_search',
            context: weContext.get(),
        }).then(function (blog_ids) {
            if (blog_ids.length === 1) {
                document.location = '/blog/' + blog_ids[0][0] + '/post/new';
            } else if (blog_ids.length > 1) {
                wUtils.prompt({
                    id: 'editor_new_blog',
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

//==============================================================================

odoo.define('website_blog.editor', function (require) {
'use strict';

require('web.dom_ready');
var weWidgets = require('web_editor.widget');
var options = require('web_editor.snippets.options');
var rte = require('web_editor.rte');

if (!$('.website_blog').length) {
    return $.Deferred().reject("DOM doesn't contain '.website_blog'");
}

rte.Class.include({
    // Destroy popOver and stop listening mouseup event on edit mode
    start: function () {
        $(".js_tweet, .js_comment").off('mouseup').trigger('mousedown');
        return this._super.apply(this, arguments);
    },
    _saveElement: function ($el, context) {
        var defs = [this._super.apply(this, arguments)];
        // TODO the o_dirty class is not put on the right element for blog cover
        // edition. For some strange reason, it was forcly put (even if not
        // dirty) in <= saas-16 but this is not the case anymore.
        var $blogContainer = $el.closest('.o_blog_cover_container');
        if (!this.__blogCoverSaved && $blogContainer.length) {
            $el = $blogContainer;
            this.__blogCoverSaved = true;
            defs.push(this._rpc({
                route: '/blog/post_change_background',
                params: {
                    post_id: parseInt($el.closest("[name=\"blog_post\"], .website_blog").find("[data-oe-model=\"blog.post\"]").first().data("oe-id"), 10),
                    cover_properties: {
                        "background-image": $el.children(".o_blog_cover_image").css("background-image").replace(/"/g, '').replace(window.location.protocol + "//" + window.location.host, ''),
                        "background-color": $el.data("filter_color"),
                        "opacity": $el.data("filter_value"),
                        "resize_class": $el.data("cover_class"),
                    },
                },
            }));
        }
        return $.when.apply($, defs);
    },
});

options.registry.many2one.include({
    _selectRecord: function ($li) {
        var self = this;
        this._super.apply(this, arguments);
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
    start: function () {
        this.$filter_value_options = this.$el.find('li[data-filter_value]');
        this.$filter_color_options = this.$el.find('li[data-filter_color]');
        this.filter_color_classes = this.$filter_color_options.map(function () {
            return $(this).data("filter_color");
        }).get().join(" ");

        return this._super.apply(this, arguments);
    },
    clear: function (previewMode, value, $li) {
        this.selectClass(previewMode, "", $());
        this.$image.css("background-image", "");
    },
    change: function (previewMode, value, $li) {
        var $image = $("<img/>", {src: this.$image.css("background-image")});

        var editor = new weWidgets.MediaDialog(this, {
            onlyImages: true,
            firstFilters: ['background']
        }, $image, $image[0]).open();
        editor.on("save", this, function (event, img) {
            var src = $image.attr("src");
            this.$image.css("background-image", src ? ("url(" + src + ")") : "");
            if (!this.$target.hasClass("cover")) {
                var $li = this.$el.find("[data-select-class]").first();
                this.selectClass(previewMode, $li.data("selectClass"), $li);
            }
            this._setActive();
        });
    },
    filter_value: function (previewMode, value, $li) {
        this.$filter.css("opacity", value);
    },
    filter_color: function (previewMode, value, $li) {
        this.$filter.removeClass(this.filter_color_classes);
        if (value) {
            this.$filter.addClass(value);
        }

        var $first_visible_filter_option = this.$filter_value_options.eq(1);
        if (parseFloat(this.$filter.css('opacity')) < parseFloat($first_visible_filter_option.data("filter_value"))) {
            this.filter_value(previewMode, $first_visible_filter_option.data("filter_value"), $first_visible_filter_option);
        }
    },
    _setActive: function () {
        this._super.apply(this, arguments);
        var self = this;

        this.$el.filter(":not([data-change])").toggleClass("hidden", !this.$target.hasClass("cover"));
        this.$el.filter("li:has(li[data-select-class])").toggleClass("hidden", this.$target.hasClass("o_list_cover"));

        this.$filter_value_options.removeClass("active");
        this.$filter_color_options.removeClass("active");

        var active_filter_value = this.$filter_value_options
            .filter(function () {
                return (parseFloat($(this).data('filter_value')).toFixed(1) === parseFloat(self.$filter.css('opacity')).toFixed(1));
            }).addClass("active").data("filter_value");

        var active_filter_color = this.$filter_color_options
            .filter(function () {
                return self.$filter.hasClass($(this).data("filter_color"));
            }).addClass("active").data("filter_color");

        this.$target.data("cover_class", this.$el.find(".active[data-select-class]").data("selectClass") || "");
        this.$target.data("filter_value", active_filter_value || 0.0);
        this.$target.data("filter_color", active_filter_color || "");
    },
});
});
