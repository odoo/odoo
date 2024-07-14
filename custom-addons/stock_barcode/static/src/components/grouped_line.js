/** @odoo-module **/

import LineComponent from "@stock_barcode/components/line";

export default class GroupedLineComponent extends LineComponent {

    get isSelected() {
        return this.line.virtual_ids.indexOf(this.env.model.selectedLineVirtualId) !== -1;
    }

    get opened() {
        return this.env.model.groupKey(this.line) === this.env.model.unfoldLineKey;
    }

    toggleSublines(ev) {
        ev.stopPropagation();
        this.env.model.toggleSublines(this.line);
    }
}
GroupedLineComponent.components = { LineComponent };
GroupedLineComponent.template = 'stock_barcode.GroupedLineComponent';
