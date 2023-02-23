/** @odoo-module **/

import publicWidget from 'web.public.widget';
import DynamicSnippet from 'website.s_dynamic_snippet';

const DynamicSnippetEvents = DynamicSnippet.extend({
    selector: '.s_event_upcoming_snippet',
    disabledInEditableMode: false,

    /**
     * @override
     * @private
     */
    _getSearchDomain: function () {
        let searchDomain = this._super.apply(this, arguments);
        const filterByTagIds = this.$el.get(0).dataset.filterByTagIds;
        if (filterByTagIds) {
            let tagGroupedByCategory = _.groupBy(JSON.parse(filterByTagIds), 'category_id');
            for (const category in tagGroupedByCategory) {
                searchDomain = searchDomain.concat(
                    [['tag_ids', 'in', tagGroupedByCategory[category].map(e => e.id)]]);
            }
        }
        return searchDomain;
    }

});

publicWidget.registry.events = DynamicSnippetEvents;
