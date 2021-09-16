odoo.define("web.ComparisonMenu", function (require) {
    "use strict";

    const { FACET_ICONS } = require("web.searchUtils");
    const { useModel } = require("web.Model");

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

    return ComparisonMenu;
});
