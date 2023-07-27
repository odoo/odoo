/** @odoo-module **/

import { groupBy } from '@web/core/utils/arrays';
import publicWidget from '@web/legacy/js/public/public_widget';
import DynamicSnippet from '@website/snippets/s_dynamic_snippet/000';

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
            let tagGroupedByCategory = groupBy(JSON.parse(filterByTagIds), 'category_id');
            for (const category in tagGroupedByCategory) {
                searchDomain = searchDomain.concat(
                    [['tag_ids', 'in', tagGroupedByCategory[category].map(e => e.id)]]);
            }
        }
        return searchDomain;
    }

});

publicWidget.registry.events = DynamicSnippetEvents;
