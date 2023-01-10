odoo.define("web.ComparisonMenu", function (require) {
    "use strict";

    const { Dropdown } = require("@web/core/dropdown/dropdown");
    const { SearchDropdownItem } = require("@web/search/search_dropdown_item/search_dropdown_item");
    const { FACET_ICONS } = require("web.searchUtils");
    const { useModel } = require("web.Model");
    const { LegacyComponent } = require("@web/legacy/legacy_component");

    class ComparisonMenu extends LegacyComponent {
        setup() {
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
         * @param {number} itemId
         */
        onComparisonSelected(itemId) {
            this.model.dispatch("toggleComparison", itemId);
        }
    }
    ComparisonMenu.template = "web.ComparisonMenu";
    ComparisonMenu.components = { Dropdown, DropdownItem: SearchDropdownItem };

    return ComparisonMenu;
});
