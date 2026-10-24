/** @odoo-module **/

import { SearchPanel } from "@web/search/search_panel/search_panel";
import { useState } from "@odoo/owl";


export class ProductCatalogSearchPanel extends SearchPanel {
    static subTemplates = {
        ...SearchPanel.subTemplates,
        filtersGroup: "ProductCatalogSearchPanel.FiltersGroup",
    };

    setup() {
        super.setup();

        this.state = useState({
            ...this.state,
            sectionOfAttributes: {},
        });
    }

    updateActiveValues() {
        super.updateActiveValues();
        this.state.sectionOfAttributes = this.buildSection();
    }

    buildSection() {
        const values = this.env.searchModel.filters[0].values;
        let sections = new Map();

        values.forEach(element => {
            const name = element.display_name;
            const id = element.id;
            // The backend groups the records that share a display name by their
            // underlying attribute value, so every record carries the same
            // per-value count; take it once instead of summing.
            const count = element.__count;

            if (count <= 0) {
                return;
            }
            if (sections.has(name)) {
                sections.get(name).get('ids').push(id);
            } else {
                let newAttr = new Map();
                newAttr.set('ids', [id]);
                newAttr.set('count', count);
                sections.set(name, newAttr);
            }
        });

        return sections;
    }

    toggleSectionFilterValue(filterId, attrIds, { currentTarget }) {
        attrIds.forEach(id => {
            this.toggleFilterValue(filterId, id, { currentTarget });
        })
    }
}
