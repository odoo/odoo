/** @odoo-module **/

import options from 'web_editor.snippets.options';
import dynamicSnippetOptions from 'website.s_dynamic_snippet_options';

const dynamicSnippetEventOptions = dynamicSnippetOptions.extend({
    /**
     * @override
     */
    init() {
        this._super.apply(this, arguments);
        this.modelNameFilter = 'event.event';
        this.tagIDs = [];
    },
    /**
     * @override
     */
    onBuilt() {
        this._super.apply(this, arguments);
        // TODO Remove in master.
        this.$target[0].dataset['snippet'] = 's_events';
    },

    async willStart() {
        const _super = this._super.bind(this);
        this.tagIDs = JSON.parse(this.$target[0].dataset.filterByTagIds || '[]');
        const tags = await this._rpc({
            model: 'event.tag',
            method: 'search_read',
            domain: ['&', ['category_id.website_published', '=', true], ['color', 'not in', ['0', false]]],
            fields: ['id', 'display_name'],
        });
        this.allTagsByID = {};
        for (const tag of tags) {
            this.allTagsByID[tag.id] = tag;
        }

        return _super(...arguments);
    },

    setTags(previewMode, widgetValue, params) {
        this.tagIDs = JSON.parse(widgetValue).map(tag => tag.id);
        this.selectDataAttribute(previewMode, JSON.stringify(this.tagIDs), params);
    },

    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        if (methodName === 'setTags') {
            return JSON.stringify(this.tagIDs.map(id => this.allTagsByID[id]));
        }
        return this._super(...arguments);
    },

    _setOptionsDefaultValues() {
        this._setOptionValue('numberOfRecords', 4);
        this._super.apply(this, arguments);
    },

});

options.registry.event_upcoming_snippet = dynamicSnippetEventOptions;
