/** @odoo-module **/

import Domain from "web.Domain";
import DomainSelectorDialog from "web.DomainSelectorDialog";
import config from "web.config";
import {getHumanDomain} from "../../js/utils.esm";
import {standaloneAdapter} from "web.OwlCompatibility";
const {Component, useRef} = owl;

class AdvancedFilterItem extends Component {
    setup() {
        this.itemRef = useRef("dropdown-item");
    }
    /**
     * Prevent propagation of dropdown-item-selected event, so that it
     * doesn't reach the FilterMenu onFilterSelected event handler.
     */
    mounted() {
        $(this.itemRef.el).on("dropdown-item-selected", (event) =>
            event.stopPropagation()
        );
    }
    /**
     * Open advanced search dialog
     *
     * @returns {DomainSelectorDialog} The opened dialog itself.
     */
    onClick() {
        const adapterParent = standaloneAdapter({Component});
        const dialog = new DomainSelectorDialog(
            adapterParent,
            this.env.searchModel.resModel,
            "[]",
            {
                debugMode: config.isDebug(),
                readonly: false,
            }
        );
        // Add 1st domain node by default
        dialog.opened(() => dialog.domainSelector._onAddFirstButtonClick());
        // Configure handler
        dialog.on("domain_selected", this, function (e) {
            const preFilter = {
                description: getHumanDomain(dialog.domainSelector),
                domain: Domain.prototype.arrayToString(e.data.domain),
                type: "filter",
            };
            this.env.searchModel.createNewFilters([preFilter]);
        });
        return dialog.open();
    }
}

AdvancedFilterItem.components = {AdvancedFilterItem};

AdvancedFilterItem.template = "web_advanced_search.AdvancedFilterItem";
export default AdvancedFilterItem;
