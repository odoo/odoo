odoo.define('website_blog.new_blog_post', function (require) {
'use strict';

var core = require('web.core');
var wUtils = require('website.utils');
var WebsiteNewMenu = require('website.newMenu');

var _t = core._t;

WebsiteNewMenu.include({
    actions: _.extend({}, WebsiteNewMenu.prototype.actions || {}, {
        new_blog_post: '_createNewBlogPost',
    }),

    //--------------------------------------------------------------------------
    // Actions
    //--------------------------------------------------------------------------

    /**
     * Asks the user information about a new blog post to create, then creates
     * it and redirects the user to this new post.
     *
     * @private
     * @returns {Promise} Unresolved if there is a redirection
     */
    _createNewBlogPost: function () {
        return this._rpc({
            model: 'blog.blog',
            method: 'name_search',
        }).then(function (blog_ids) {
            if (blog_ids.length === 1) {
                document.location = '/blog/' + blog_ids[0][0] + '/post/new';
                return new Promise(function () {});
            } else if (blog_ids.length > 1) {
                return wUtils.prompt({
                    id: 'editor_new_blog',
                    window_title: _t("New Blog Post"),
                    select: _t("Select Blog"),
                    init: function (field) {
                        return blog_ids;
                    },
                }).then(function (result) {
                    var blog_id = result.val;
                    if (!blog_id) {
                        return;
                    }
                    document.location = '/blog/' + blog_id + '/post/new';
                    return new Promise(function () {});
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
var weWidgets = require('wysiwyg.widgets');
var options = require('web_editor.snippets.options');
var WysiwygMultizone = require('web_editor.wysiwyg.multizone');

if (!$('.website_blog').length) {
    return Promise.reject("DOM doesn't contain '.website_blog'");
}

WysiwygMultizone.include({
    /**
     * @override
     */
    start: function () {
        $('.js_tweet, .js_comment').off('mouseup').trigger('mousedown');
        _.each($('.oe_structure[data-editor-message!="False"]'), function (el) {
            if (!$.trim($(el).html()).length) {
                $(el).empty();
            }
            $(el).toggleClass('oe_empty', !$.trim($(el).html()).length);
        });
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _saveElement: function (outerHTML, recordInfo, editable) {
        var prom = this._super.apply(this, arguments);

        var el = editable.closest('.o_blog_cover_container');
        if (!el) {
            return prom;
        }

        var ancestor = el.closest('[name="blog_post"], #o_wblog_blog_top, #o_wblog_post_top');
        var blogID = parseInt($(ancestor.querySelector('[data-oe-model="blog.blog"]')).data('oe-id'), 10);
        var postID = parseInt($(ancestor.querySelector('[data-oe-model="blog.post"]')).data('oe-id'), 10);

        if (blogID) {
            this.__savedCoversBlogIDs = this.__savedCoversBlogIDs || [];
            if (this.__savedCoversBlogIDs.includes(blogID)) {
                return prom;
            }
            this.__savedCoversBlogIDs.push(blogID);
        }
        if (postID) {
            this.__savedCoversPostIDs = this.__savedCoversPostIDs || [];
            if (this.__savedCoversPostIDs.includes(postID)) {
                return prom;
            }
            this.__savedCoversPostIDs.push(postID);
        }

        var model = postID ? 'blog.post' : blogID ? 'blog.blog' : false;
        if (!model) {
            return prom;
        }

        var cssBgImage = $(el.querySelector('.o_blog_cover_image')).css('background-image');
        var coverProps = {
            'background-image': cssBgImage.replace(/"/g, '').replace(window.location.protocol + "//" + window.location.host, ''),
            'background-color': el.dataset.filterColor,
            'opacity': el.dataset.filterValue,
            'resize_class': el.dataset.coverClass,
            'text_size_class': el.dataset.textSizeClass,
            'text_align_class': el.dataset.textAlignClass,
        };

        var prom2 = this._rpc({
            model: model,
            method: 'write',
            args: [
                postID || blogID,
                {'cover_properties': JSON.stringify(coverProps)}
            ],
        });

        return Promise.all([prom, prom2]);
    },
});

options.registry.many2one.include({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _selectRecord: function ($opt) {
        var self = this;
        this._super.apply(this, arguments);
        if (this.$target.data('oe-field') === 'author_id') {
            var $nodes = $('[data-oe-model="blog.post"][data-oe-id="'+this.$target.data('oe-id')+'"][data-oe-field="author_avatar"]');
            $nodes.each(function () {
                var $img = $(this).find('img');
                var css = window.getComputedStyle($img[0]);
                $img.css({ width: css.width, height: css.height });
                $img.attr('src', '/web/image/res.partner/'+self.ID+'/image_1024');
            });
            setTimeout(function () { $nodes.removeClass('o_dirty'); },0);
        }
    }
});

options.registry.blog_cover = options.Class.extend({
    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);

        this.$image = this.$target.find('.o_blog_cover_image');
        this.$filter = this.$target.find('.o_blog_cover_filter');
    },
    /**
     * @override
     */
    start: function () {
        this.$filterValueOpts = this.$el.find('[data-filter-value]');
        this.$filterColorOpts = this.$el.find('[data-filter-color]');
        this.filterColorClasses = this.$filterColorOpts.map(function () {
            return $(this).data('filterColor');
        }).get().join(' ');

        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @see this.selectClass for parameters
     */
    clear: function (previewMode, value, $opt) {
        this.selectClass(previewMode, '', $());
        this.$image.css('background-image', '');
    },
    /**
     * @see this.selectClass for parameters
     */
    change: function (previewMode, value, $opt) {
        var $image = $('<img/>');
        var background = this.$image.css('background-image');
        if (background && background !== 'none') {
            $image.attr('src', background.match(/^url\(["']?(.+?)["']?\)$/)[1]);
        }

        var editor = new weWidgets.MediaDialog(this, {
            mediaWidth: 1920,
            onlyImages: true,
            firstFilters: ['background']
        }, $image[0]).open();
        editor.on('save', this, function (image) {
            var src = image.src;
            this.$image.css('background-image', src ? ('url(' + src + ')') : '');
            if (!this.$target.hasClass('o_wblog_has_cover')) {
                var $opt = this.$el.find('.o_wblog_cover_opt_size_default[data-select-class]');
                this.selectClass(previewMode, $opt.data('selectClass'), $opt);
            }
            this._setActive();
        });
    },
    /**
     * @see this.selectClass for parameters
     */
    filterValue: function (previewMode, value, $opt) {
        this.$filter.css('opacity', value);
    },
    /**
     * @see this.selectClass for parameters
     */
    filterColor: function (previewMode, value, $opt) {
        this.$filter.removeClass(this.filterColorClasses);
        if (value) {
            this.$filter.addClass(value);
        }

        var $firstVisibleFilterOpt = this.$filterValueOpts.eq(1);
        if (parseFloat(this.$filter.css('opacity')) < parseFloat($firstVisibleFilterOpt.data('filterValue'))) {
            this.filterValue(previewMode, $firstVisibleFilterOpt.data('filterValue'), $firstVisibleFilterOpt);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @override
     */
    _setActive: function () {
        this._super.apply(this, arguments);
        var self = this;
        var isRegularCover = this.$target.is('.o_wblog_post_page_cover_regular');

        _.each(this.$el.children(), function (el) {
            var $el = $(el);

            if (!$el.is('[data-change]')) {
                $el.removeClass('d-none');

                ['size', 'filters', 'text_size', 'text_align'].forEach(optName => {
                    var $opts = $el.find('[data-cover-opt="' + optName + '"]');
                    var notAllowed = (self.$target.data('use_' + optName) !== 'True');

                    if ($opts.length && (!self.$target.hasClass('o_wblog_has_cover') || notAllowed)) {
                        $el.addClass('d-none');
                    }
                });
            }
            $el.find('.o_js_hide_regular').toggleClass('d-none', isRegularCover);
            $el.find('.o_js_show_regular').toggleClass('d-none', !isRegularCover);
        });

        this.$el.find('[data-clear]').toggleClass('d-none', !self.$target.hasClass('o_wblog_has_cover'));

        this.$filterValueOpts.removeClass('active');
        this.$filterColorOpts.removeClass('active');

        var activeFilterValue = this.$filterValueOpts
            .filter(function () {
                return (parseFloat($(this).data('filterValue')).toFixed(1) === parseFloat(self.$filter.css('opacity')).toFixed(1));
            }).addClass('active').data('filterValue');

        var activeFilterColor = this.$filterColorOpts
            .filter(function () {
                return self.$filter.hasClass($(this).data('filterColor'));
            }).addClass('active').data('filterColor');

        this.$target[0].dataset.coverClass = this.$el.find('.active[data-cover-opt="size"]').data('selectClass') || '';
        this.$target[0].dataset.textSizeClass = this.$el.find('.active[data-cover-opt="text_size"]').data('selectClass') || '';
        this.$target[0].dataset.textAlignClass = this.$el.find('.active[data-cover-opt="text_align"]').data('selectClass') || '';
        this.$target[0].dataset.filterValue = activeFilterValue || 0.0;
        this.$target[0].dataset.filterColor = activeFilterColor || '';
    },
});
});
