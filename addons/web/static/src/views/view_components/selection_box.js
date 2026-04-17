import { Component } from "@odoo/owl";
import { useLayoutEffect } from "@web/owl2/utils";

export class SelectionBox extends Component {
    static components = {};
    static template = "web.SelectionBox";
    static props = {
        root: { type: Object },
    };
    setup() {
        this.root = this.props.root;
        useLayoutEffect(() => {
            this.env.bus.trigger("STICKY_NAVBAR:RESET_STATE", { isDocked: true });
            return () => this.env.bus.trigger("STICKY_NAVBAR:RESET_STATE", { isDocked: false });
        });
    }
    get nbSelected() {
        return this.selectedRecords.length;
    }
    get nbTotal() {
        return this.root.isGrouped ? this.root.recordCount : this.root.count;
    }
    get hasLimitedCount() {
        return this.root.hasLimitedCount;
    }
    get isDomainSelected() {
        return this.root.isDomainSelected;
    }
    get isPageSelected() {
        return (
            this.nbSelected === this.root.records.length &&
            (!this.isRecordCountTrustable || this.nbTotal > this.selectedRecords.length)
        );
    }
    get isRecordCountTrustable() {
        return this.root.isRecordCountTrustable;
    }
    get selectedRecords() {
        return this.root.selection;
    }
    onUnselectAll() {
        this.selectedRecords.forEach((record) => {
            record.toggleSelection(false);
        });
        this.root.selectDomain(false);
    }
    onSelectDomain() {
        this.root.selectDomain(true);
    }
}
