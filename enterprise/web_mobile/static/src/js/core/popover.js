/** @odoo-module **/

import { Popover } from "@web/core/popover/popover";
import { useBackButton } from "@web_mobile/js/core/hooks";
import { patch } from "@web/core/utils/patch";

patch(Popover.prototype, {
    setup() {
        super.setup(...arguments);
        useBackButton(this.onBackButton.bind(this), () => this.props.target.isConnected);
    },

    //---------------------------------------------------------------------
    // Handlers
    //---------------------------------------------------------------------

    /**
     * Close popover on back-button
     * @private
     */
    onBackButton() {
        this.props.close();
    },
});
