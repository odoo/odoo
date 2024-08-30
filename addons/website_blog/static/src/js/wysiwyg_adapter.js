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
