/** @odoo-module **/

import { SearchPanel } from "@web/search/search_panel/search_panel";
import { useState } from "@odoo/owl";


export class ProductCatalogSearchPanel extends SearchPanel {
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
            const count = element.__count;

            if (sections.has(name)) {
                let currentAttr = sections.get(name);
                currentAttr.get('ids').push(id);
                currentAttr.set('count', currentAttr.get('count') + count);
            } else if (count > 0) {
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

ProductCatalogSearchPanel.subTemplates = {
    ...SearchPanel.subTemplates,
    filtersGroup: "ProductCatalogSearchPanel.FiltersGroup",
}
