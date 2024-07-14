/** @odoo-module **/

import { Component } from "@odoo/owl";

export default class LineComponent extends Component {
    get destinationLocationPath () {
        return this._getLocationPath(this.env.model._defaultDestLocation(), this.line.location_dest_id);
    }

    get displayDestinationLocation() {
        return !this.props.subline && this.env.model.displayDestinationLocation;
    }

    get displayResultPackage() {
        return this.env.model.displayResultPackage;
    }

    get displaySourceLocation() {
        return !this.props.subline && this.env.model.displaySourceLocation;
    }

    get highlightLocation() {
        return this.env.model.lastScanned.sourceLocation &&
               this.env.model.lastScanned.sourceLocation.id == this.line.location_id.id;
    }

    get isComplete() {
        if (!this.qtyDemand || this.qtyDemand != this.qtyDone) {
            return false;
        } else if (this.isTracked && !this.lotName) {
            return false;
        }
        return true;
    }

    get isSelected() {
        return this.line.virtual_id === this.env.model.selectedLineVirtualId ||
        (this.line.package_id && this.line.package_id.id === this.env.model.lastScanned.packageId);
    }

    get isTracked() {
        return this.line.product_id.tracking !== 'none';
    }

    get lotName() {
        return (this.line.lot_id && this.line.lot_id.name) || this.line.lot_name || '';
    }

    get nextExpected() {
        if (!this.isSelected) {
            return false;
        } else if (this.isTracked && !this.lotName) {
            return 'lot';
        } else if (this.qtyDemand && this.qtyDone < this.qtyDemand) {
            return 'quantity';
        }
    }

    get qtyDemand() {
        return this.env.model.getQtyDemand(this.line);
    }

    get qtyDone() {
        return this.env.model.getQtyDone(this.line);
    }

    get quantityIsSet() {
        return this.line.inventory_quantity_set;
    }

    get incrementQty() {
        return this.env.model.getIncrementQuantity(this.line);
    }

    get line() {
        return this.props.line;
    }

    get sourceLocationPath() {
        return this._getLocationPath(this.env.model._defaultLocation(), this.line.location_id);
    }

    get componentClasses() {
        return [
            this.isComplete ? 'o_line_completed' : 'o_line_not_completed',
            this.env.model.lineIsFaulty(this.line) ? 'o_faulty' : '',
            this.isSelected ? 'o_selected o_highlight' : ''
        ].join(' ');
    }

    _getLocationPath(rootLocation, currentLocation) {
        let locationName = currentLocation.display_name;
        if (this.env.model.shouldShortenLocationName && this.env.model._isSublocation &&
            this.env.model._isSublocation(currentLocation, rootLocation) &&
            rootLocation && rootLocation.id != currentLocation.id) {
            locationName = locationName.replace(rootLocation.display_name, '...');
        }
        return locationName.replace(new RegExp(currentLocation.name + '$'), '');
    }

    addQuantity(quantity, ev) {
        this.env.model.updateLineQty(this.line.virtual_id, quantity);
    }

    select(ev) {
        ev.stopPropagation();
        this.env.model.selectLine(this.line);
        this.env.model.trigger('update');
    }

    setOnHandQuantity(ev) {
        this.env.model.setOnHandQuantity(this.line);
    }
}
LineComponent.props = ["displayUOM", "line", "subline?", "editLine"];
LineComponent.template = 'stock_barcode.LineComponent';
