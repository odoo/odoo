odoo.define("web.ComparisonMenu", function (require) {
    "use strict";

    const { FACET_ICONS } = require("web.searchUtils");
    const { useModel } = require("web.Model");
    const { SearchDropdownItem } = require("@web/search/search_dropdown_item/search_dropdown_item");

    const { Component } = owl;

    class ComparisonMenu extends Component {
        constructor() {
            super(...arguments);
            this.icon = FACET_ICONS.comparison;
            this.model = useModel('searchModel');
        }

        /**
         * @override
         */
        get items() {
            return this.model.get('filters', f => f.type === 'comparison');
        }

        /**
         * @private
         * @param {OwlEvent} ev
         */
        onComparisonSelected(ev) {
            const { itemId } = ev.detail.payload;
            this.model.dispatch("toggleComparison", itemId);
        }
    }
    ComparisonMenu.template = "web.ComparisonMenu";
    ComparisonMenu.components = { DropdownItem: SearchDropdownItem };

    return ComparisonMenu;
});
