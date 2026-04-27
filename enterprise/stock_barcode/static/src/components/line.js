/** @odoo-module **/

import { Component } from "@odoo/owl";
import { ProductImageDialog } from '@stock_barcode/components/product_image_dialog';

export default class LineComponent extends Component {
    static props = ["displayUOM", "line", "subline?", "editLine"];
    static template = "stock_barcode.LineComponent";

    setup() {
        this.imageSource = this.props.line.product_id.has_image
            ? `/web/image/product.product/${this.props.line.product_id.id}/image_128`
            : null;
    }

    get destinationLocationPath () {
        return this._getLocationPath(this.env.model._defaultDestLocation(), this.line.location_dest_id);
    }

    get displayDeleteButton() {
        return this.env.model.lineCanBeDeleted(this.line);
    }

    get displayDestinationLocation() {
        return !this.props.subline && this.env.model.displayDestinationLocation;
    }

    get displayFulfillbutton() {
        return this.incrementQty && this.env.model.getDisplayIncrementBtn(this.line);
    }

    get displayIncrementButton() {
        if (this.isSelected && this.incrementQty !== 1) {
            return this.isTracked && this.line.product_id.tracking === "serial"
                ? this.env.model.getDisplayIncrementBtnForSerial(this.line)
                : this.env.model.getDisplayIncrementBtn(this.line);
        }
        return false;
    }

    get incrementQty() {
        return this.env.model.getIncrementQuantity(this.line);
    }

    get displayResultPackage() {
        return this.env.model.displayResultPackage;
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
        return this.env.model.lineIsSelected(this.line) ||
        (this.line.package_id && this.line.package_id.id === this.env.model.lastScanned.packageId);
    }

    get isTracked() {
        return this.env.model.lineIsTracked(this.line);
    }

    get lotName() {
        if (this.env.model.showReservedSns || this.env.model.getQtyDone(this.line)) {
            return (this.line.lot_id && this.line.lot_id.name) || this.line.lot_name || "";
        }
        return "";
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

    get line() {
        return this.props.line;
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

    addQuantity(quantity) {
        let lineVirtualId = this.line.virtual_id;
        if (this.line.lines?.length > 1 && this.lotName) {
            lineVirtualId = this.line.lines.find((subline) => {
                const sublineLotName = subline.lot_id ? subline.lot_id.name : subline.lot_name;
                return sublineLotName === this.lotName;
            }).virtual_id;
        }
        this.env.model.updateLineQty(lineVirtualId, quantity);
    }

    select(ev) {
        ev.stopPropagation();
        this.env.model.selectLine(this.line);
        this.env.model.trigger('update');
    }

    toggleAsCounted(ev) {
        this.env.model.toggleAsCounted(this.line);
    }

    onClickImage() {
        this.env.dialog.add(ProductImageDialog, { record: this.line.product_id });
    }
}
