/** @odoo-module **/

import BarcodePickingModel from '@stock_barcode/models/barcode_picking_model';
import { _t } from "@web/core/l10n/translation";
import { session } from '@web/session';

export default class BarcodePickingBatchModel extends BarcodePickingModel {
    constructor(params) {
        super(...arguments);
        this.formViewReference = 'stock_barcode_picking_batch.stock_barcode_batch_picking_view_info';
        this.validateMessage = _t("The Batch Transfer has been validated");
        this.validateMethod = 'action_done';
    }

    setData(data) {
        super.setData(...arguments);
        this.formViewId = data.data.form_view_id;
        // In case it's a new batch, we must display the pickings selector first.
        if (this.record.state === 'draft' && this.record.picking_ids.length === 0) {
            this.selectedPickings = [];
            this._allowedPickings = data.data.allowed_pickings;
            this.pickingTypes = data.data.picking_types;
            for (const picking of this._allowedPickings) {
                if (picking.user_id) {
                    picking.user_id = this.cache.getRecord('res.users', picking.user_id);
                }
            }
            if (!this.record.picking_type_code) {
                this.selectedPickingTypeId = false;
            }
        }
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    get allowedPickings() {
        const pickingTypeId = this.record.picking_type_id;
        if (!pickingTypeId || !this._allowedPickings) {
            return [];
        }
        return this._allowedPickings.filter(picking => picking.picking_type_id === pickingTypeId);
    }

    askBeforeNewLinesCreation(product) {
        return product && !this.currentState.lines.some(line => line.product_id.id === product.id);
    }

    get backordersDomain() {
        return [["backorder_id", "in", this.record.picking_ids]];
    }

    get barcodeInfo() {
        const barcodeInfo = {};
        if ((this.needPickings || this.needPickingType) && !this._allowedPickings.length) {
            // Special case: the batch need to be configured but there is no pickings available.
            barcodeInfo.class = "picking_batch_not_possible";
            barcodeInfo.message = _t("No ready transfers found");
            barcodeInfo.warning = true;
        } else if (this.needPickingType) {
            barcodeInfo.class = "picking_batch_select_type";
            barcodeInfo.message = _t("Select an operation type for batch transfer");
        } else if (this.needPickings) {
            barcodeInfo.class = "picking_batch_select_transfers";
            barcodeInfo.message = _t("Select transfers for batch transfer");
        } else if (this.isDone) {
            barcodeInfo.class = "picking_already_done";
            barcodeInfo.message = _t("This batch transfer is already done");
            barcodeInfo.warning = true;
        } else if (this.isCancelled) {
            barcodeInfo.class = "picking_already_cancelled";
            barcodeInfo.message = _t("This batch transfer is cancelled");
            barcodeInfo.warning = true;
        } else if (this.record.state === 'draft') {
            barcodeInfo.class = "picking_batch_draft";
            barcodeInfo.message =  _t("This batch transfer is still draft, it must be confirmed before being processed");
            barcodeInfo.warning = true;
        }
        if (barcodeInfo.message) {
            barcodeInfo.icon = barcodeInfo.warning ? "exclamation-triangle" : "hand-pointer-o";
            barcodeInfo.warning = true;
        }
        return barcodeInfo.message ? barcodeInfo : super.barcodeInfo;
    }

    get canBeProcessed() {
        if (this.record.state === 'draft') {
            return this.needPickingType || this.needPickings;
        }
        return super.canBeProcessed;
    }

    get cancelLabel() {
        return _t("Cancel Batch Transfer");
    }

    get canConfirmSelection() {
        if (this.needPickingType) {
            return Boolean(this.selectedPickingTypeId);
        } else if (this.needPickings) {
            return Boolean(this.selectedPickings.length);
        }
    }

    /**
     * Depending of the batch's state, will confirm the picking type selection or the pickings
     * selection. In the latter, it will confirm the batch transfer and reload its data.
     */
    async confirmSelection() {
        if (this.needPickingType && this.selectedPickingTypeId) {
            // Applies the selected picking type to the batch.
            this.record.picking_type_id = this.selectedPickingTypeId;
            this.trigger('update');
        } else if (this.needPickings && this.selectedPickings.length) {
            // Adds the selected pickings to the batch.
            const data = await this.orm.call(
                'stock.picking.batch',
                'action_add_pickings_and_confirm',
                [[this.resId],
                {
                    picking_type_id: this.record.picking_type_id,
                    picking_ids: this.selectedPickings,
                    state: 'in_progress',
                }]
            );
            await this.refreshCache(data.records);
            this.selectedPickings = [];
            this.config = data.config || {}; // Get the picking type's scan restrictions configuration.
            this.trigger('update');
        }
    }

    get canCreateNewLot() {
        return this.picking.use_create_lots;
    }

    groupKey(line) {
        return `${line.picking_id.id}_` + super.groupKey(...arguments);
    }

    get needPickings() {
        return this.record.state === 'draft' && this.record.picking_ids.length === 0;
    }

    get needPickingType() {
        return this.record.state === 'draft' && !this.record.picking_type_id;
    }

    get printButtons() {
        return [{
            name: _t("Print Batch Transfer"),
            class: 'o_print_picking_batch',
            method: 'action_print',
        }];
    }

    get reloadingMoveLines() {
        return super.reloadingMoveLines && !this.selectedPickings?.length;
    }

    selectOption(id) {
        if (this.needPickingType) { // Selects a picking type.
            this.selectedPickingTypeId = this.selectedPickingTypeId === id ? false : id;
            this.trigger('update');
        } else if (this.needPickings) { // Selects a picking.
            if (this.selectedPickings.indexOf(id) !== -1) {
                // If picking already selected, removes it from the selected ones.
                this.selectedPickings.splice(this.selectedPickings.indexOf(id), 1);
            } else {
                this.selectedPickings.push(id);
            }
            this.trigger('update');
        }
    }

    get useExistingLots() {
        return this.picking.use_existing_lots;
    }

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------

    _getLinesToMove() {
        const configScanProd = this.config.restrict_scan_product;
        const configScanDest = this.config.restrict_scan_dest_location;
        const lines = super._getLinesToMove();
        // We may have multiple pickings in a batch which move the same product,
        // then we should just update them all together.
        if (configScanDest === 'mandatory' && configScanProd) {
            lines.push(...this.previousScannedLines);
        }
        return Array.from(new Set(lines));
    }

    async _assignEmptyPackage(line, resultPackage) {
        await super._assignEmptyPackage(...arguments);
        this._suggestPackages();
    }

    _cancelNotification() {
        this.notification(_t("The batch picking has been cancelled"));
    }

    _canOverrideTrackingNumber(line, newLotName) {
        return super._canOverrideTrackingNumber(...arguments) || this.getQtyDone(line) === 0;
    }

    _createLinesState() {
        const lines = super._createLinesState();
        const pickings = this.record.picking_ids;
        this.colorByPickingId = new Map(pickings.map((p, i) => [p, i * (360 / pickings.length)]));

        for (const line of lines) {
            line.colorLine = this.colorByPickingId.get(line.picking_id);
            line.picking_id = line.picking_id && this.cache.getRecord('stock.picking', line.picking_id);
        }
        return lines;
    }

    _createState() {
        super._createState(...arguments);
        this._suggestPackages();
        if (this.record.picking_ids.length < 1) {
            return new Error("No picking related");
        }
        // Get the first picking as a reference for some fields the batch hasn't.
        this.picking = this.cache.getRecord('stock.picking', this.record.picking_ids[0]);
    }

    _defaultLocation() {
        return this.picking && this.cache.getRecord('stock.location', this.picking.location_id);
    }

    _defaultDestLocation() {
        return this.picking && this.cache.getRecord('stock.location', this.picking.location_dest_id);
    }

    _getNewLineDefaultValues(fieldsParams) {
        // Adds the default picking id and its corresponding color on the line.
        const defaultValues = super._getNewLineDefaultValues(...arguments);
        let line = this.selectedLine;
        if (!line) {
            if (this.lastScanned.packageId) {
                const lines = this._moveEntirePackage() ? this.packageLines : this.pageLines;
                line = lines.find(l => l.package_id && l.package_id.id === this.lastScanned.packageId);
            } else if (this.pageLines.length) {
                line = this.pageLines[0];
            }
        }
        // Get the line's picking as the default one, or take the batch's first one.
        const defaultPicking = (line && line.picking_id) || this.picking;
        defaultValues.colorLine = this.colorByPickingId.get(defaultPicking.id);
        defaultValues.picking_id = defaultPicking;
        return defaultValues;
    }

    _getNewLineDefaultContext() {
        const defaultContextValues = super._getNewLineDefaultContext();
        defaultContextValues.default_batch_id = this.record.id;
        defaultContextValues.default_picking_id = this.record.picking_ids[0];
        return defaultContextValues;
    }

    _getScanPackageMessage(line) {
        if (line && line.suggested_package) {
            return _t("Scan the package %s", line.suggested_package);
        }
        return super._getScanPackageMessage(...arguments);
    }

    _incrementTrackedLine() {
        return !(this.picking.use_create_lots || this.picking.use_existing_lots);
    }

    _moveEntirePackage() {
        return this.picking && this.picking.picking_type_entire_packs;
    }

    _sortingMethod(l1, l2) {
        const res = super._sortingMethod(...arguments);
        if (res) {
            return res;
        }
        // Sort by picking's name.
        const picking1 = l1.picking_id && l1.picking_id.name || '';
        const picking2 = l2.picking_id && l2.picking_id.name || '';
        if (picking1 < picking2) {
            return -1;
        } else if (picking1 > picking2) {
            return 1;
        }
        return 0;
    }

    _suggestPackages() {
        const suggestedPackagesByPicking = {};
        // Checks if a line has a result package, and if so, links it to the according picking.
        for (const line of this.currentState.lines) {
            if (line.result_package_id && !suggestedPackagesByPicking[line.picking_id.id]) {
                suggestedPackagesByPicking[line.picking_id.id] = line.result_package_id.name;
            }
        }
        // Suggests a package to scan for each picking's line if its picking is linked to a package.
        for (const line of this.currentState.lines) {
            if (!line.result_package_id && suggestedPackagesByPicking[line.picking_id.id]) {
                line.suggested_package = suggestedPackagesByPicking[line.picking_id.id];
            }
        }
    }

    /**
     * Set the batch's responsible if the batch or one of its picking is unassigned.
     */
    async _setUser() {
        if (this._shouldAssignUser()) {
            this.record.user_id = session.uid;
            const pickings = [];
            for (const pickingId of this.record.picking_ids) {
                const picking = this.cache.getRecord('stock.picking', pickingId);
                picking.user_id = session.uid;
                pickings.push(picking);
            }
            this.cache.setCache({'stock.picking': pickings});
            await this.orm.write(this.resModel, [this.record.id], { user_id: session.uid });
        }
    }

    _shouldAssignUser() {
        // First checks if user should be assigned to batch...
        if (this.record.user_id != session.uid)
            return true;
        // ... then checks if user should be assigned to atleast one picking.
        for (const pickingId of this.record.picking_ids) {
            const picking = this.cache.getRecord('stock.picking', pickingId);
            if (picking.user_id != session.uid)
                return true;
        }
        return false;
    }

}
