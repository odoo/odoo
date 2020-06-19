odoo.define("web.ComparisonMenu", function (require) {
    "use strict";

    const DropdownMenu = require("web.DropdownMenu");
    const { FACET_ICONS } = require("web.searchUtils");
    const { useModel } = require("web.model");

    /**
     * "Comparison" menu
     *
     * Displays a set of comparison options related to the currently selected
     * date filters.
     * @extends DropdownMenu
     */
    class ComparisonMenu extends DropdownMenu {
        constructor() {
            super(...arguments);
            this.model = useModel("controlPanelModel");
        }

        //---------------------------------------------------------------------
        // Getters
        //---------------------------------------------------------------------

        /**
         * @override
         */
        get icon() {
            return FACET_ICONS.comparison;
        }

        /**
         * @override
         */
        get items() {
            return this.model.getFiltersOfType("comparison");
        }

        /**
         * @override
         */
        get title() {
            return this.env._t("Comparison");
        }

        //---------------------------------------------------------------------
        // Handlers
        //---------------------------------------------------------------------

        /**
         * @private
         * @param {OwlEvent} ev
         */
        _onItemSelected(ev) {
            ev.stopPropagation();
            const { item } = ev.detail;
            this.model.dispatch("toggleComparison", item.id);
        }

    }

    return ComparisonMenu;
});
