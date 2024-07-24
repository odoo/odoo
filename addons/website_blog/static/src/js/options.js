/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import options from "@web_editor/js/editor/snippets.options.legacy";
import { SnippetOption } from "@web_editor/js/editor/snippets.options";
import {
    CoverProperties,
} from "@website/js/editor/snippets.options";
import {
    registerWebsiteOption,
} from "@website/js/editor/snippets.registry";
import { uniqueId } from "@web/core/utils/functions";
import { patch } from "@web/core/utils/patch";

const NEW_TAG_PREFIX = 'new-blog-tag-';

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
            var $nodes = $('[data-oe-model="blog.post"][data-oe-id="' + this.$target.data('oe-id') + '"][data-oe-field="author_avatar"]');
            $nodes.each(function () {
                var $img = $(this).find('img');
                var css = window.getComputedStyle($img[0]);
                $img.css({width: css.width, height: css.height});
                $img.attr('src', '/web/image/res.partner/' + self.ID + '/avatar_1024');
            });
            setTimeout(function () {
                $nodes.removeClass('o_dirty');
            }, 0);
        }
    }
});

patch(CoverProperties.prototype, {
    /**
     * @override
     */
    async _getRenderContext() {
        const context = await super._getRenderContext();
        context.isBlogCover = this.$target[0].classList.contains('o_wblog_post_page_cover');
        context.isRegularCover = this.$target.is('.o_wblog_post_page_cover_regular');
        return context;
    }
});

export class BlogPostTagSelection extends SnippetOption {
    /**
     * @override
     */
    async willStart() {
        this.blogPostID = parseInt(this.$target[0].dataset.blogId);
        this.isEditingTags = false;
        const tags = await this.env.services.orm.searchRead(
            "blog.tag",
            [],
            ["id", "name", "display_name", "post_ids"]
        );
        this.allTagsByID = {};
        this.tagIDs = [];
        for (const tag of tags) {
            this.allTagsByID[tag.id] = tag;
            if (tag['post_ids'].includes(this.blogPostID)) {
                this.tagIDs.push(tag.id);
            }
        }

        return super.willStart(...arguments);
    }
    /**
     * @override
     */
    cleanForSave() {
        this._notifyUpdatedTags();
    }

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @see this.selectClass for params
     */
    setTags(previewMode, widgetValue, params) {
        if (this._preventNextSetTagsCall) {
            this._preventNextSetTagsCall = false;
            return;
        }
        this.tagIDs = JSON.parse(widgetValue).map(tag => tag.id);
    }
    /**
     * @see this.selectClass for params
     */
    createTag(previewMode, widgetValue, params) {
        if (!widgetValue) {
            return;
        }
        const existing = Object.values(this.allTagsByID).some(tag => {
            // A tag is already existing only if it was already defined (i.e.
            // id is a number) or if it appears in the current list of tags.
            return tag.name.toLowerCase() === widgetValue.toLowerCase()
                && (typeof(tag.id) === 'number' || this.tagIDs.includes(tag.id));
        });
        if (existing) {
            return this.env.services.notification.add(_t("This tag already exists"), {
                type: 'warning',
            });
        }
        const newTagID = uniqueId(NEW_TAG_PREFIX);
        this.allTagsByID[newTagID] = {
            'id': newTagID,
            'name': widgetValue,
            'display_name': widgetValue,
        };
        this.tagIDs.push(newTagID);
        // TODO Find a smarter way to achieve this.
        // Because of the invocation order of methods, setTags will be called
        // after createTag. This would reset the tagIds to the value before
        // adding the newly created tag. It therefore needs to be prevented.
        this._preventNextSetTagsCall = true;
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        if (methodName === 'setTags') {
            return JSON.stringify(this.tagIDs.map(id => this.allTagsByID[id]));
        }
        return super._computeWidgetState(...arguments);
    }
    /**
     * @private
     */
    _notifyUpdatedTags() {
        this.options.wysiwyg._onSetBlogPostUpdatedTags(
            this.blogPostID,
            this.tagIDs.map(tagID => this.allTagsByID[tagID]),
        );
    }
}

registerWebsiteOption("BlogPostTagSelection", {
    Class: BlogPostTagSelection,
    template: "website_blog.blog_post_tag_selection_option",
    selector: ".o_wblog_post_page_cover",
    target: "#o_wblog_post_name",
    noCheck: true,
});

registerWebsiteOption("BlogPostListPageOption", {
    selector: "main:has(#o_wblog_index_content)",
    template: "website_blog.blog_list_page_option",
    noCheck: true,
    data: {
        string: _t("Blogs Page"),
        pageOptions: true,
        groups: ["website.group_website_designer"],
    },
});

registerWebsiteOption("BlogPostPageOption", {
    selector: "main:has(#o_wblog_post_main)",
    template: "website_blog.blog_post_page_option",
    noCheck: true,
    data: {
        string: _t("Blog Page"),
        pageOptions: true,
        groups: ["website.group_website_designer"],
    },
});

// Hides ContainerWidth option for content in blog posts
const ContainerWidthOption = registry.category("snippet_options").get("container_width");
ContainerWidthOption.exclude = ContainerWidthOption.exclude + ", #o_wblog_post_content *";
registry.category("snippet_options").add("container_width", ContainerWidthOption, { force: true });
