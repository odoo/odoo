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
            method: 'search_read',
            args: [wUtils.websiteDomain(this), ['name']],
        }).then(function (blogs) {
            if (blogs.length === 1) {
                document.location = '/blog/' + blogs[0]['id'] + '/post/new';
                return new Promise(function () {});
            } else if (blogs.length > 1) {
                return wUtils.prompt({
                    id: 'editor_new_blog',
                    window_title: _t("New Blog Post"),
                    select: _t("Select Blog"),
                    init: function (field) {
                        return _.map(blogs, function (blog) {
                            return [blog['id'], blog['name']];
                        });
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
const {qweb, _t} = require('web.core');
const options = require('web_editor.snippets.options');
var WysiwygMultizone = require('web_editor.wysiwyg.multizone');

if (!$('.website_blog').length) {
    return Promise.reject("DOM doesn't contain '.website_blog'");
}

const NEW_TAG_PREFIX = 'new-blog-tag-';

WysiwygMultizone.include({
    custom_events: Object.assign({}, WysiwygMultizone.prototype.custom_events, {
        'set_blog_post_updated_tags': '_onSetBlogPostUpdatedTags',
    }),

    /**
     * @override
     */
    init() {
        this._super(...arguments);
        this.blogTagsPerBlogPost = {};
    },
    /**
     * @override
     */
    async start() {
        await this._super(...arguments);
        $('.js_tweet, .js_comment').off('mouseup').trigger('mousedown');
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async save() {
        const ret = await this._super(...arguments);
        await this._saveBlogTags(); // Note: important to be called after save otherwise cleanForSave is not called before
        return ret;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Saves the blog tags in the database.
     *
     * @private
     */
    async _saveBlogTags() {
        for (const [key, tags] of Object.entries(this.blogTagsPerBlogPost)) {
            const proms = tags.filter(tag => typeof tag.id === 'string').map(tag => {
                return this._rpc({
                    model: 'blog.tag',
                    method: 'create',
                    args: [{
                        'name': tag.name,
                    }],
                });
            });
            const createdIDs = await Promise.all(proms);

            await this._rpc({
                model: 'blog.post',
                method: 'write',
                args: [parseInt(key), {
                    'tag_ids': [[6, 0, tags.filter(tag => typeof tag.id === 'number').map(tag => tag.id).concat(createdIDs)]],
                }],
            });
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onSetBlogPostUpdatedTags: function (ev) {
        this.blogTagsPerBlogPost[ev.data.blogPostID] = ev.data.tags;
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

options.registry.CoverProperties.include({
    /**
     * @override
     */
    updateUI: async function () {
        await this._super(...arguments);
        var isRegularCover = this.$target.is('.o_wblog_post_page_cover_regular');
        var $coverFull = this.$el.find('[data-select-class*="o_full_screen_height"]');
        var $coverMid = this.$el.find('[data-select-class*="o_half_screen_height"]');
        var $coverAuto = this.$el.find('[data-select-class*="cover_auto"]');
        this._coverFullOriginalLabel = this._coverFullOriginalLabel || $coverFull.text();
        this._coverMidOriginalLabel = this._coverMidOriginalLabel || $coverMid.text();
        this._coverAutoOriginalLabel = this._coverAutoOriginalLabel || $coverAuto.text();
        $coverFull.children('div').text(isRegularCover ? _t("Large") : this._coverFullOriginalLabel);
        $coverMid.children('div').text(isRegularCover ? _t("Medium") : this._coverMidOriginalLabel);
        $coverAuto.children('div').text(isRegularCover ? _t("Tiny") : this._coverAutoOriginalLabel);
    },
});

options.registry.BlogPostTagSelection = options.Class.extend({
    xmlDependencies: (options.Class.prototype.xmlDependencies || [])
        .concat(['/website_blog/static/src/xml/website_blog_tag.xml']),

    /**
     * @override
     */
    async willStart() {
        const _super = this._super.bind(this);

        this.blogPostID = parseInt(this.$target[0].dataset.blogId);
        this.isEditingTags = false;
        const tags = await this._rpc({
            model: 'blog.tag',
            method: 'search_read',
            args: [[], ['id', 'name', 'post_ids']],
        });
        this.allTagsByID = {};
        this.tagIDs = [];
        for (const tag of tags) {
            this.allTagsByID[tag.id] = tag;
            if (tag['post_ids'].includes(this.blogPostID)) {
                this.tagIDs.push(tag.id);
            }
        }

        return _super(...arguments);
    },
    /**
     * @override
     */
    cleanForSave() {
        if (this.isEditingTags) {
            this._notifyUpdatedTags();
        }
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @see this.selectClass for params
     */
    editTagList(previewMode, widgetValue, params) {
        this.isEditingTags = true;
        this.rerender = true;
    },
    /**
     * Send changes that will be saved in the database.
     *
     * @see this.selectClass for params
     */
    saveTagList(previewMode, widgetValue, params) {
        this.isEditingTags = false;
        this.rerender = true;
        this._notifyUpdatedTags();
    },
    /**
     * @see this.selectClass for params
     */
    setNewTagName(previewMode, widgetValue, params) {
        this.newTagName = widgetValue;
    },
    /**
     * @see this.selectClass for params
     */
    confirmNew(previewMode, widgetValue, params) {
        if (!this.newTagName) {
            return;
        }
        const existing = Object.values(this.allTagsByID).some(tag => tag.name.toLowerCase() === this.newTagName.toLowerCase());
        if (existing) {
            return this.displayNotification({
                type: 'warning',
                message: _t("This tag already exists"),
            });
        }
        const newTagID = _.uniqueId(NEW_TAG_PREFIX);
        this.allTagsByID[newTagID] = {
            'id': newTagID,
            'name': this.newTagName,
        };
        this.tagIDs.push(newTagID);
        this.newTagName = '';
        this.rerender = true;
    },
    /**
     * @see this.selectClass for params
     */
    addTag(previewMode, widgetValue, params) {
        const tagID = parseInt(widgetValue);
        this.tagIDs.push(tagID);
        this.rerender = true;
    },
    /**
     * @see this.selectClass for params
     */
    removeTag(previewMode, widgetValue, params) {
        this.tagIDs = this.tagIDs.filter(tagID => (`${tagID}` !== widgetValue));
        if (widgetValue.startsWith(NEW_TAG_PREFIX)) {
            delete this.allTagsByID[widgetValue];
        }
        this.rerender = true;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async updateUI() {
        if (this.rerender) {
            this.rerender = false;
            await this._rerenderXML();
            return;
        }
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _computeWidgetVisibility(widgetName, params) {
        if (['blog_existing_tag_opt', 'new_tag_input_opt', 'new_tag_button_opt', 'save_tags_opt'].includes(widgetName)) {
            return this.isEditingTags;
        }
        if (widgetName === 'edit_tags_opt') {
            return !this.isEditingTags;
        }
        if (params.optionsPossibleValues['removeTag']) {
            return this.isEditingTags;
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        if (methodName === 'addTag') {
            // The related widget allows to select a value but then resets its state to a non-selected value
            return '';
        }
        return this._super(...arguments);
    },
    /**
     * @private
     */
    _notifyUpdatedTags() {
        this.trigger_up('set_blog_post_updated_tags', {
            blogPostID: this.blogPostID,
            tags: this.tagIDs.map(tagID => this.allTagsByID[tagID]),
        });
    },
    /**
     * @override
     */
    async _renderCustomXML(uiFragment) {
        const $tagList = $(uiFragment.querySelector('.o_wblog_tag_list'));
        for (const tagID of this.tagIDs) {
            const tag = this.allTagsByID[tagID];
            $tagList.append(qweb.render('website_blog.TagListItem', {
                tag: tag,
            }));
        }
        const $select = $(uiFragment.querySelector('we-select[data-name="blog_existing_tag_opt"]'));
        for (const [key, tag] of Object.entries(this.allTagsByID)) {
            if (this.tagIDs.includes(parseInt(key))) {
                continue;
            }
            $select.prepend(qweb.render('website_blog.TagSelectItem', {
                tag: tag,
            }));
        }
    },
});
});
