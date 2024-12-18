import { _t } from "@web/core/l10n/translation";
import options from "@web_editor/js/editor/snippets.options";
import "@website/js/editor/snippets.options";
import { uniqueId } from "@web/core/utils/functions";

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

options.registry.CoverProperties.include({
    /**
     * @override
     */
    updateUI: async function () {
        const isBlogCover = this.$target[0].classList.contains('o_wblog_post_page_cover');
        if (!isBlogCover) {
            return this._super(...arguments);
        }
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
        return this._super(...arguments);
    },
});

options.registry.BlogPostTagSelection = options.Class.extend({
    init() {
        this._super(...arguments);
        this.orm = this.bindService("orm");
        this.notification = this.bindService("notification");
    },

    /**
     * @override
     */
    async willStart() {
        const _super = this._super.bind(this);

        this.blogPostID = parseInt(this.$target[0].dataset.blogId);
        this.isEditingTags = false;
        const tags = await this.orm.searchRead(
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

        return _super(...arguments);
    },  
    /**
     * @override
     */
    cleanForSave() {
        this._notifyUpdatedTags();
    },

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
    },
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
            return this.notification.add(_t("This tag already exists"), {
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
    async _computeWidgetState(methodName, params) {
        if (methodName === 'setTags') {
            return JSON.stringify(this.tagIDs.map(id => this.allTagsByID[id]));
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
        uiFragment.querySelector('we-many2many').dataset.recordId = this.blogPostID;
    },
});
