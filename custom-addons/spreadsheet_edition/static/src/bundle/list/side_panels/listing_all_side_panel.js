/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { ListingDetailsSidePanel } from "./listing_details_side_panel";

import { Component, onWillUpdateProps } from "@odoo/owl";

export class ListingAllSidePanel extends Component {
    setup() {
        this.getters = this.env.model.getters;
        onWillUpdateProps(() => {
            if (!this.env.model.getters.getListIds().length) {
                this.props.onCloseSidePanel();
            }
        });
    }

    selectListing(listId) {
        this.env.model.dispatch("SELECT_ODOO_LIST", { listId });
    }

    resetListingSelection() {
        this.env.model.dispatch("SELECT_ODOO_LIST");
    }

    delete(listId) {
        this.env.askConfirmation(_t("Are you sure you want to delete this list?"), () => {
            this.env.model.dispatch("REMOVE_ODOO_LIST", { listId });
            this.props.onCloseSidePanel();
        });
    }
}
ListingAllSidePanel.template = "spreadsheet_edition.ListingAllSidePanel";
ListingAllSidePanel.components = { ListingDetailsSidePanel };
ListingAllSidePanel.props = {
    onCloseSidePanel: Function,
    listId: { type: String, optional: true },
};
