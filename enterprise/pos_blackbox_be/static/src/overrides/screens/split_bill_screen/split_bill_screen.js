/** @odoo-module **/

import { SplitBillScreen } from "@pos_restaurant/app/split_bill_screen/split_bill_screen";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

/**
 * Prevent refunding work in/out lines.
 */
patch(SplitBillScreen.prototype, {
    setup() {
        super.setup();
        this.ui = useService("ui");
    },
    async preSplitOrder(originalOrder, newOrder) {
        try {
            this.ui.block();
            if (this.pos.useBlackBoxBe()) {
                await this.pos.pushCorrection(originalOrder);
            }
        } finally {
            this.ui.unblock();
        }
    },
    async postSplitOrder(originalOrder, newOrder) {
        try {
            this.ui.block();
            if (this.pos.useBlackBoxBe()) {
                await this.pos.pushProFormaOrderLog(originalOrder);
                await this.pos.pushProFormaOrderLog(newOrder);
            }
        } finally {
            this.ui.unblock();
        }
    },
});
