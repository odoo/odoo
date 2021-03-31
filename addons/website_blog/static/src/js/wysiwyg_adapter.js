import { WysiwygAdapterComponent } from '@website/components/wysiwyg_adapter/wysiwyg_adapter';
import { patch } from "@web/core/utils/patch";


patch(WysiwygAdapterComponent.prototype, {
    /**
     * @override
     */
    init() {
        super.init(...arguments);
        this.blogTagsPerBlogPost = {};
    },
    /**
     * @override
     */
    async startEdition() {
        await super.startEdition(...arguments);
        this.options.document.defaultView.$('.js_tweet, .js_comment').off('mouseup').trigger('mousedown');

        const postContentEl = this.$editable[0].querySelector('.o_wblog_post_content_field');
        if (postContentEl) {
            // Adjust size of some elements once some content changes:
            // - the snippet order changes because the first text might become
            //   a different one,
            // - the class changes because this is where the content width
            //   option is set.
            this._widthObserver = new MutationObserver(records => {
                const consideredUpdates = records.some(record => {
                    // Only consider DOM structure modification and class
                    // changes.
                    return record.type === 'childList'
                        || (record.type === 'attributes' && record.attributeName === 'class');
                });
                if (consideredUpdates) {
                    // TODO Replace event once edited document's core.bus can be reached.
                    this.$editable[0].querySelector('.website_blog').dispatchEvent(
                        new CustomEvent('blog_width_update')
                    );
                }
            });
            this._widthObserver.observe(postContentEl, {
                childList: true,
                subtree: true,
                attributes: true,
            });
        }
    },
    /**
     * @override
     */
    destroy() {
        if (this._widthObserver) {
            this._widthObserver.disconnect();
        }
        return super.destroy(...arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _saveViewBlocks() {
        const ret = await super._saveViewBlocks(...arguments);
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
                return this.orm.create("blog.tag", [{
                        'name': tag.name,
                    }]);
            });
            const createdIDs = (await Promise.all(proms)).flat();

            await this.orm.write("blog.post", [parseInt(key)], {
                'tag_ids': [[6, 0, tags.filter(tag => typeof tag.id === 'number').map(tag => tag.id).concat(createdIDs)]],
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

    /**
     * @override
     */
    _trigger_up(ev) {
        if (ev.name === 'set_blog_post_updated_tags') {
            this._onSetBlogPostUpdatedTags(ev);
            return;
        } else {
            return super._trigger_up(...arguments);
        }
    },
});
