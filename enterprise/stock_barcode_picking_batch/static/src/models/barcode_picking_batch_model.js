/** @odoo-module **/

import BarcodePickingModel from '@stock_barcode/models/barcode_picking_model';
import { formatFloat } from "@web/core/utils/numbers";
import { _t } from "@web/core/l10n/translation";
import { user } from '@web/core/user';

export default class BarcodePickingBatchModel extends BarcodePickingModel {
    constructor(params) {
        super(...arguments);
        this.formViewReference = 'stock_barcode_picking_batch.stock_barcode_batch_picking_view_info';
        this.validateMessage = _t("The Batch Transfer has been validated");
        this.validateMethod = 'action_done';
    }

    setData(data) {
        super.setData(...arguments);
        this.groupingLinesEnabled = this.groupingLinesEnabled || this.config.group_lines_by_product;
        // In case it's a new batch, we must display the pickings selector first.
        if (this.record.state === 'draft' && this.record.picking_ids.length === 0) {
            this.selectedPickings = [];
            this._allowedPickings = data.data.allowed_pickings;
            this.pickingTypes = data.data.records["stock.picking.type"];
            for (const picking of this._allowedPickings) {
                if (picking.user_id) {
                    picking.user_id = this.cache.getRecord('res.users', picking.user_id);
                }
                if (picking.batch_id) {
                    picking.batch_id = this.cache.getRecord('stock.picking.batch', picking.batch_id);
                }
                if (picking.partner_id) {
                    picking.partner_id = this.cache.getRecord('res.partner', picking.partner_id);
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
        const pickingTypeId = this.record.picking_type_id.id;
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
            this.record.picking_type_id = this.cache.getRecord("stock.picking.type", this.selectedPickingTypeId);
            this.trigger('update');
        } else if (this.needPickings && this.selectedPickings.length) {
            // Adds the selected pickings to the batch.
            const data = await this.orm.call(
                'stock.picking.batch',
                'action_add_pickings_and_confirm',
                [[this.resId],
                {
                    picking_type_id: this.record.picking_type_id.id,
                    picking_ids: this.selectedPickings,
                    state: 'in_progress',
                }]
            );
            await this.refreshCache(data.records);
            this.selectedPickings = [];
            this.config = { ...this.config, ...(data.config || {}) }; // Get the picking type's scan restrictions configuration.
            this.trigger('update');
        }
    }

    async processBarcode(barcode) {
        // scans should be ignored until the batch has been created
        if (this.record.state == "draft") {
            this.notification(
                _t(
                    "This batch transfer is still in draft, scans are disabled until the batch is confirmed"
                ),
                { type: "danger" }
            );
        } else if (this.isDone) {
            return this.notification(_t("This batch is already done"), { type: "danger" });
        } else if (this.isCancelled) {
            return this.notification(_t("This batch is already cancelled"), { type: "danger" });
        } else {
            return super.processBarcode(barcode);
        }
    }

    get canCreateNewLot() {
        return this.picking.use_create_lots;
    }

    displayLineQtyDemand(line) {
        if (this.config.group_lines_by_product && this.getQtyDemand(line) && line.batchParentLine) {
            return true;
        }
        return super.displayLineQtyDemand(line);
    }

    get displaySignatureButton() {
        return false;
    }

    groupLines() {
        const groupedLines = super.groupLines();
        if (this.config.group_lines_by_product) {
            // Make a second grouping by product.
            const lines = [...groupedLines];
            const param = { digits: [false, this.precision], thousandsSep: "", decimalPoint: "." };
            const groupedLinesByKey = {};
            for (let index = lines.length - 1; index >= 0; index--) {
                const line = lines[index];
                const key = super.groupKey(line);
                if (!groupedLinesByKey[key]) {
                    groupedLinesByKey[key] = [];
                }
                if (line.batchParentLine) {
                    // Remove previous parent line's link.
                    delete line.batchParentLine;
                }
                const linesToPush = line.lines ? line.lines : [line];
                lines.splice(index, 1);
                groupedLinesByKey[key].push(...linesToPush);
            }
            for (const sublines of Object.values(groupedLinesByKey)) {
                if (sublines.length === 1) {
                    lines.push(...sublines);
                    continue;
                }
                const ids = [];
                const virtual_ids = [];
                let [qtyDemand, qtyDone] = [0, 0];
                for (const subline of sublines) {
                    ids.push(subline.id);
                    virtual_ids.push(subline.virtual_id);
                    qtyDemand += this.getQtyDemand(subline);
                    qtyDone += this.getQtyDone(subline);
                }
                const groupedLine = this._groupBatchSublines(
                    sublines,
                    ids,
                    virtual_ids,
                    parseFloat(formatFloat(qtyDemand, param)),
                    parseFloat(formatFloat(qtyDone, param))
                );
                lines.push(groupedLine);
            }
            this._groupedLines = this._sortLine(lines);
            return this._groupedLines;
        }
        return groupedLines;
    }

    _groupBatchSublines(sublines, ids, virtual_ids, qtyDemand, qtyDone) {
        const sortedSublines = this._sortLine(sublines);
        // Use the line with lowest ID as the reference (info shown on summary
        // line and also the move line opened for the form view.)
        const referenceLine = sortedSublines.reduce((result, line) => {
            return line.id && (!result.id || (result.id > line.id)) ? line : result;
        })
        const groupedLine = Object.assign({}, referenceLine, {
            ids,
            lines: sortedSublines,
            opened: false,
            virtual_ids,
            reserved_uom_qty: qtyDemand,
            qty_done: qtyDone,
        });
        for (const subline of sublines) {
            subline.batchParentLine = groupedLine;
        }
        return groupedLine;
    }

    groupKey(line) {
        return `${line.picking_id.id}_` + super.groupKey(...arguments);
    }

    lineCannotBeGrouped(line) {
        if (this.config.group_lines_by_product) {
            return Boolean(line.lines);
        }
        return super.lineCannotBeGrouped(...arguments);
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
        }, {
            name: _t("Print Product Labels"),
            class: 'o_print_picking_batch_labels',
            method: 'action_open_label_layout',
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

    get shouldOpenSignatureModal() {
        return false;
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
            if (!this.config.group_lines_by_product) {
                // Don't color lines if they are grouped by product/locations (lines from different
                // pickings can be grouped together so it makes no sense.)
                line.colorLine = this.colorByPickingId.get(line.picking_id);
            }
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

    _findLine(barcodeData) {
        // With batch pickings, we can have multiple grouped lines for the same tracked product if
        // different pickings use the same tracked product. This override ensures once the user
        // started to scan lot/serial numbers for a grouped line, we complete it before looking for
        // another grouped line, even if the scanned LN/SN is reserved in another picking.
        const {lot, lotName, product} = barcodeData;
        const dataLotName = lotName || (lot && lot.name) || false;
        if (this.selectedLine && this.selectedLine.product_id.id === product.id && dataLotName) {
            const parentLine = this._getParentLine(this.selectedLine);
            if (parentLine && this._lineIsNotComplete(parentLine)) {
                let foundLine = false;
                const hasLotLessLine = parentLine.lines.some(
                    (line) => !line.lot_id && !line.lot_name
                );
                for (const line of parentLine.lines) {
                    const lineLotName = line.lot_name || (line.lot_id && line.lot_id.name) || false;
                    const sameLotName = Boolean(lineLotName && dataLotName === lineLotName);
                    if (
                        this._canOverrideTrackingNumber(line, dataLotName) &&
                        (!sameLotName || this._lineIsNotComplete(line) || !hasLotLessLine)
                    ) {
                        foundLine = line;
                        if (sameLotName) {
                            // Prioritize this line if it has the scanned lot.
                            break;
                        }
                    }
                }
                return foundLine;
            }
        }
        return super._findLine(...arguments);
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
        const defaultPicking =
            (fieldsParams && fieldsParams.picking_id) || (line && line.picking_id) || this.picking;
        if (!this.config.group_lines_by_product) {
            // Don't add the color if lines are grouped by product.
            defaultValues.colorLine = this.colorByPickingId.get(defaultPicking.id);
        }
        defaultValues.picking_id = defaultPicking;
        return defaultValues;
    }

    _getNewLineDefaultContext() {
        const defaultContextValues = super._getNewLineDefaultContext(...arguments);
        defaultContextValues.default_batch_id = this.record.id;
        defaultContextValues.default_picking_id = this.record.picking_ids[0];
        return defaultContextValues;
    }

    _getScanPackageMessage(line) {
        if (line?.suggested_package) {
            return _t("Scan the package %s", line.suggested_package);
        }
        return super._getScanPackageMessage(...arguments);
    }

    _incrementTrackedLine() {
        return !(this.picking.use_create_lots || this.picking.use_existing_lots);
    }

    _lineCannotBeTaken(line) {
        // Don't take another line if the selected one is not complete and are from different pickings.
        let selectedLine = this.selectedLine;
        if (selectedLine && selectedLine.product_id?.tracking !== "none") {
            selectedLine = this._getParentLine(selectedLine) || selectedLine;
        }
        return (
            selectedLine &&
            line.product_id.id === selectedLine.product_id.id &&
            selectedLine.qty_done < selectedLine.reserved_uom_qty &&
            line.picking_id.id != selectedLine.picking_id.id
        );
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
            this.record.user_id = user.userId;
            const pickings = [];
            for (const pickingId of this.record.picking_ids) {
                const picking = this.cache.getRecord('stock.picking', pickingId);
                picking.user_id = user.userId;
                pickings.push(picking);
            }
            this.cache.setCache({'stock.picking': pickings});
            await this.orm.write(this.resModel, [this.record.id], { user_id: user.userId });
        }
    }

    _shouldAssignUser() {
        // First checks if user should be assigned to batch...
        if (this.record.user_id != user.userId)
            return true;
        // ... then checks if user should be assigned to atleast one picking.
        for (const pickingId of this.record.picking_ids) {
            const picking = this.cache.getRecord('stock.picking', pickingId);
            if (picking.user_id != user.userId)
                return true;
        }
        return false;
    }

}
