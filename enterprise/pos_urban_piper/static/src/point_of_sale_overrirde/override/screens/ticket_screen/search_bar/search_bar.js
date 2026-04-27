import { useEffect } from "@odoo/owl";
import { SearchBar } from "@point_of_sale/app/screens/ticket_screen/search_bar/search_bar";
import { patch } from "@web/core/utils/patch";

patch(SearchBar.prototype, {
    setup() {
        super.setup(...arguments);
        useEffect(
            () => {
                this.state.selectedFilter =
                    this.props.config.defaultFilter || this.filterOptionsList[0];
            },
            () => [this.props.config.defaultFilter]
        );
    },
});
