/** @odoo-module **/

import { BarcodeParser } from "@barcodes/js/barcode_parser";
import { Mutex } from "@web/core/utils/concurrency";
import { formatFloat } from "@web/core/utils/numbers";
import LazyBarcodeCache from '@stock_barcode/lazy_barcode_cache';
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { FNC1_CHAR } from "@barcodes_gs1_nomenclature/js/barcode_parser";
import { EventBus } from "@odoo/owl";
import { BarcodeObject } from "../barcode_object";

export default class BarcodeModel extends EventBus {
    constructor(resModel, resId, services) {
        super();
        this.dialogService = useService('dialog');
        this.orm = services.orm;
        this.notificationService = services.notification;
        this.action = services.action;
        this.resId = resId;
        this.resModel = resModel;
        this.unfoldLineKey = false;
        this.currentSortIndex = 0;
        this.validateContext = {};
        // Keeps the history of all barcodes scanned (start with the most recent.)
        this.scanHistory = [];
        // Keeps track of list scanned record(s) by type.
        this.lastScanned = { packageId: false, product: false, sourceLocation: false };
        this._currentLocation = false; // Reminds the current source when the scanned one is forgotten.
        this.needSourceConfirmation = false;
        this.useTrackingNumber = true;
        this.uriCache = new Set(); // Avoid to scan multiple times the same URI.
        this.notificationCache = new Set(); // Avoid to display same notification
    }

    setData(data) {
        this.actionId = data.actionId;
        this.cache = new LazyBarcodeCache(data.data.records);
        const nomenclature = this.cache.getRecord('barcode.nomenclature', data.data.nomenclature_id);
        nomenclature.rules = [];
        for (const ruleId of nomenclature.rule_ids) {
            nomenclature.rules.push(this.cache.getRecord('barcode.rule', ruleId));
        }
        this.parser = new BarcodeParser({ nomenclature });
        BarcodeObject.setEnv(this.cache, this.parser);
        this.scannedLinesVirtualId = [];

        this.actionMutex = new Mutex();
        this.config = data.data.config || {};
        this.groups = data.groups;
        this.groupingLinesEnabled = this.groups.group_production_lot;

        this.packageTypes = [];
        if (this.groups.group_tracking_lot) { // Get the package types by barcode.
            const packageTypes = this.cache.dbBarcodeCache['stock.package.type'] || {};
            for (const [barcode, ids] of Object.entries(packageTypes)) {
                this.packageTypes.push([barcode, ids[0]]);
            }
        }

        this._createState();
        this.linesToSave = [];
        this.selectedLineVirtualId = false;

        // UI stuff.
        this.name = this._getName();
        // Barcode's commands are returned by a method for override purpose.
        this.commands = this._getCommands();
    }

    // GETTER

    getQtyDone(line) {
        throw new Error('Not Implemented');
    }

    getQtyDemand(line) {
        throw new Error('Not Implemented');
    }

    getDisplayIncrementBtn(line) {
        return true;
    }

    getDisplayIncrementBtnForSerial(line) {
        return !(line.lot_id || line.lot_name) || this.getQtyDone(line) === 0;
    }

    getDisplayIncrementPackagingBtn(line) {
        return false;
    }

    getActionRefresh(newId) {
        return {
            route: '/stock_barcode/get_barcode_data',
            params: {model: this.resModel, res_id: this.resId || false},
        };
    }

    getIncrementQuantity(line) {
        let remainingQty = this.getLineRemainingQuantity(line);
        const params = { digits: [false, this.precision], thousandsSep: "", decimalPoint: "." };
        return parseFloat(formatFloat(remainingQty, params));
    }

    getLineRemainingQuantity(line) {
        return this.getQtyDemand(line) ? this.getQtyDemand(line) - this.getQtyDone(line) : 0;
    }

    getlotName(line) {
        return (line.lot_id && line.lot_id.name) || line.lot_name || false;
    }

    getEditedLineParams(line) {
        return { currentId: line.id };
    }

    async apply() {
        throw new Error('Not Implemented');
    }

    get barcodeInfo() {
        throw new Error('Not Implemented');
    }

    get canCreateNewLot() {
        return true;
    }

    get canBeProcessed() {
        return true;
    }

    get isValidForBarcodeLookup() {
        return true;
    }

    /**
     * The operation can be validated if there is at least one line.
     * @returns {boolean}
     */
    get canBeValidate() {
        return this.pageLines.length + this.packageLines.length;
    }

    get cancelLabel() {
        return _t("Cancel");
    }

    get canSelectLocation() {
        return true;
    }

    get displayAddProductButton() {
        return true;
    }

    get displayApplyButton() {
        return false;
    }

    get displayCancelButton() {
        return false;
    }

    get displaySignatureButton() {
        return false;
    }

    get displayDestinationLocation() {
        return false;
    }

    get displayReturnButton() {
        return false;
    }

    get useScanDestinationLocation() {
        return this.displayDestinationLocation;
    }

    get showReservedSns() {
        return true;
    }

    get displayResultPackage() {
        return false;
    }

    get displaySourceLocation() {
        return this.groups.group_stock_multi_locations;
    }

    get useScanSourceLocation() {
        return this.displaySourceLocation;
    }

    displayLineQtyDemand(line) {
        return this.getQtyDemand(line);
    }

    groupKey(line) {
        return `${line.product_id.id}_${line.location_id.id}`;
    }

    lineCannotBeGrouped(line) {
        // Don't try to group a line who is not tracked or is already grouped.
        return line.product_id.tracking === 'none' || line.lines;
    }

    /**
     * Returns the page's lines but with tracked products grouped by product id.
     *
     * @returns
     */
    get groupedLines() {
        this.groupLines();
        return this._groupedLines;
    }

    groupLines() {
        if (!this.groupingLinesEnabled) {
            this._groupedLines = this._sortLine(this.pageLines);
            return this._groupedLines;
        }
        const lines = [...this.pageLines];
        const groupedLinesByKey = {};
        const param = { digits: [false, this.precision], thousandsSep: "", decimalPoint: "." };
        for (let index = lines.length - 1; index >= 0; index--) {
            const line = lines[index];
            if (line.parentLine) {
                // Remove previous parent line's link.
                delete line.parentLine;
            }
            if (this.lineCannotBeGrouped(line)) {
                continue;
            }
            const key = this.groupKey(line);
            if (!groupedLinesByKey[key]) {
                groupedLinesByKey[key] = [];
            }
            groupedLinesByKey[key].push(...lines.splice(index, 1));
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
            const groupedLine = this._groupSublines(
                sublines,
                ids,
                virtual_ids,
                parseFloat(formatFloat(qtyDemand, param)),
                parseFloat(formatFloat(qtyDone, param))
            );
            lines.push(groupedLine);
        }
        // Before to return the line, we sort them to have new lines always on
        // top and complete lines always on the bottom.
        this._groupedLines = this._sortLine(lines);
        return this._groupedLines;
    }

    getLineLocation(line) {
        // Determine whether to group lines by source or destination location.
        return line.location_id;
    }

    get groupedLinesByLocation() {
        const lines = [].concat(this.groupedLines, this.packageLines);
        const linesByLocations = []
        const linesByLocation = {};
        for (const line of lines) {
            const lineLoc = this.getLineLocation(line);
            if (!linesByLocation[lineLoc.id]) {
                linesByLocation[lineLoc.id] = {
                    location: lineLoc,
                    lines: [],
                };
            }
            if (!linesByLocations.includes(linesByLocation[lineLoc.id])) {
                linesByLocations.push(linesByLocation[lineLoc.id]);
            }
            linesByLocation[lineLoc.id].lines.push(line);
        }
        // Sorts groups to ensure that locations will always follow the alphabetical order.
        linesByLocations.sort((lblA, lblB) => {
            const [locNameA, locNameB] = [lblA.location.display_name, lblB.location.display_name];
            return locNameA < locNameB ? -1 : locNameA > locNameB ? 1 : 0;
        });
        return linesByLocations
    }

    get highlightValidateButton() {
        return false;
    }

    get isDone() {
        return false;
    }

    get isCancelled() {
        return false;
    }

    displaySetButton(_line) {
        return false;
    }

    /**
     * Say if the line quantity is not set. Only useful for the inventory adjustment.
     *
     * @param {Object} line
     * @returns {boolean}
     */
    IsNotSet(line) {
        return false;
    }

    get lastScannedLine() {
        if (this.scannedLinesVirtualId.length) {
            const virtualId = this.scannedLinesVirtualId[this.scannedLinesVirtualId.length - 1];
            return this.currentState.lines.find(l => l.virtual_id === virtualId);
        }
        return false;
    }

    lineCanBeDeleted(line) {
        return !this.getQtyDemand(line);
    }

    lineIsFaulty(line) {
        throw new Error('Not Implemented');
    }

    lineIsTracked(line) {
        return this.useTrackingNumber && line.product_id.tracking !== 'none';
    }

    get location() {
        if (this.lastScanned.sourceLocation) { // Get last scanned location.
            return this.cache.getRecord('stock.location', this.lastScanned.sourceLocation.id);
        }
        // Get last defined source location (if applicable) or the default location.
        return this._currentLocation || this._defaultLocation();
    }
    set location(location) {
        this._currentLocation = location;
        this.lastScanned.sourceLocation = location;
    }

    get pageLines() {
        return this.currentState.lines;
    }

    get packageLines() {
        return [];
    }

    get previousScannedLines() {
        const lines = [];
        const alreadyDone = [];
        for (const virtualId of this.scannedLinesVirtualId) {
            if (alreadyDone.includes(virtualId)) {
                continue;
            }
            alreadyDone.push(virtualId);
            const foundLine = this.currentState.lines.find(l => l.virtual_id === virtualId);
            if (foundLine) {
                lines.push(foundLine);
            }
        }
        if (this.groups.group_stock_packaging) {
            lines.push(...this.previousScannedLinesByPackage);
        }
        return lines;
    }

    get previousScannedLinesByPackage() {
        if (this.lastScanned.packageId) {
            return this.currentState.lines.filter(l => l.package_id && l.package_id.id === this.lastScanned.packageId);
        }
        return [];
    }

    get printButtons() {
        throw new Error('Not Implemented');
    }

    get recordIds() {
        return [this.resId];
    }

    get selectedLine() {
        return this.selectedLineVirtualId && this.currentState.lines.find(
            l => (l.dummy_id || l.virtual_id) === this.selectedLineVirtualId
        );
    }

    get useExistingLots() {
        return true;
    }

    get validateButtonLabel() {
        return _t("Validate");
    }

    // ACTIONS

    /**
     * @param {integer} [lineId] if provided it checks if the line still exist (selects it or removes it from the lines' list)
     */
    async displayBarcodeLines(lineId) {
        if (lineId) { // If we pass a record id checks if the record still exist.
            const res = await this.orm.search(this.lineModel, [['id', '=', lineId]]);
            if (!res.length) { // The record was deleted, we remove the corresponding line.
                const lineIndex = this.currentState.lines.findIndex(l => l.id == lineId);
                this.currentState.lines.splice(lineIndex, 1);
            } else { // If it still exist, selects the record's line.
                const line = this.currentState.lines.find(line => line.id === lineId);
                this.selectLine(line);
            }
        }
    }

    /**
     * Searches for a line in the current source location. Will favor a line with no quantity
     * (or less than expected) as we assume this kind of line still need to be processed.
     * @returns {Object | Boolean} Returns a matching line or false.
     */
    findLineForCurrentLocation() {
        if (!this.lastScanned.sourceLocation) {
            return false; // Can't find anything if no location was scanned.
        }
        let foundLine = false;
        for (const line of this.pageLines) {
            if (line.location_id.id != this.lastScanned.sourceLocation.id) {
                continue; // Not the same location.
            }
            const [ qtyDone, qtyDemand ] = [this.getQtyDone(line), this.getQtyDemand(line)];
            if (qtyDone == 0 || (qtyDemand && qtyDone < qtyDemand)) {
                return line.lot_id ? this._getParentLine(line) : line; // If the line still need to be processed, returns it immediately.
            }
            foundLine = !foundLine || qtyDone < this.getQtyDone(foundLine) ? line : foundLine;
        }
        return foundLine.lot_id ? this._getParentLine(foundLine) : foundLine;
    }

    /**
     * Calls the notification service and plays a sound if the notification's type is "warning".
     * @param {String} message
     * @param {Object} options
     */
    notification(message, options={}) {
        if (this.notificationCache.has(message)) {
            return; // Don't display the notification if it's already displayed.
        }
        this.notificationCache.add(message);
        if (options.type === "danger") {
            this.trigger("playSound", "error");
        }
        return this.notificationService.add(message, options);
    }

    async refreshCache(records) {
        this.cache.setCache(records);
        this._createState();
    }

    beforeQuit() {
        return this.save();
    }

    async save() {
        const { route, params } = this._getSaveCommand();
        if (route) {
            const res = await rpc(route, params);
            await this.refreshCache(res.records);
        }
        this.linesToSave = [];
    }

    selectLine(line) {
        if (this.lineCanBeSelected(line) && (!line.virtual_ids || !line.virtual_ids.includes(this.selectedLineVirtualId))) {
            this._selectLine(line);
        }
    }

    selectPackageLine(packageLine) {
        if (this.lineCanBeSelected(packageLine)) {
            this.lastScanned.packageId = packageLine.package_id.id;
        }
    }

    toggleSublines(line) {
        const lineKey = this.groupKey(line);
        this.unfoldLineKey = this.unfoldLineKey === lineKey ? false : lineKey;
        if (this.unfoldLineKey === lineKey && (!this.selectedLine || this.unfoldLineKey != this.groupKey(this.selectedLine))) {
            this.selectLine(line);
        }
        this.trigger('update');
    }

    createSingleLinesForPackaging(barcodeData) {
        return (
            barcodeData.product.tracking === "serial" &&
            barcodeData.packaging &&
            (this.useExistingLots || this.canCreateNewLot)
        );
    }

    async updateLine(line, args) {
        let { location_id, lot_id, owner_id, package_id, reserved_uom_qty } = args;
        if (!line) {
            throw new Error('No line found');
        }
        if (!line.product_id && args.product_id) {
            line.product_id = args.product_id;
            line.product_uom_id = this.cache.getRecord('uom.uom', args.product_id.uom_id);
        }
        if (location_id) {
            if (typeof location_id === 'number') {
                location_id = this.cache.getRecord('stock.location', args.location_id);
            }
            line.location_id = location_id;
        }
        if (lot_id) {
            if (typeof lot_id === 'number') {
                lot_id = this.cache.getRecord('stock.lot', args.lot_id);
            }
            line.lot_id = lot_id;
        }
        if (owner_id) {
            if (typeof owner_id === 'number') {
                owner_id = this.cache.getRecord('res.partner', args.owner_id);
            }
            line.owner_id = owner_id;
        }
        if (package_id) {
            if (typeof package_id === 'number') {
                package_id = this.cache.getRecord('stock.quant.package', args.package_id);
            }
            line.package_id = package_id;
        }
        if (args.lot_name && line.product_id.tracking !== "none") {
            await this.updateLotName(line, args.lot_name);
            if (line.lot_id?.name != line.lot_name) {
                line.lot_id = false;
            }
        }
        if (reserved_uom_qty) {
            line.reserved_uom_qty = reserved_uom_qty;
        }
        this._updateLineQty(line, args);
        this._markLineAsDirty(line);
    }

    /**
     * Can be called by the user from the application. As the quantity field hasn't
     * the same name for all models, this method must be overridden by each model.
     *
     * @param {number} virtualId
     * @param {number} qty Quantity to increment (1 by default)
     */
    updateLineQty(virtualId, qty = 1) {
        throw new Error('Not Implemented');
    }

    async updateLotName(line, lotName) {
        // Checks if the tracking number isn't already used.
        for (const l of this.pageLines) {
            if (line.virtual_id === l.virtual_id ||
                line.product_id.tracking !== 'serial' || line.product_id.id !== l.product_id.id) {
                continue;
            }
            if (lotName === l.lot_name || (l.lot_id && lotName === l.lot_id.name)) {
                this.notification(_t("This serial number is already used."), { type: "warning" });
                return;
            }
        }
        await this._updateLotName(line, lotName);
    }

    async validate() {
        return this.actionMutex.exec(async () => this._validate());
    }

    async _validate() {
        await this.save();
        const context = this.validateContext;
        context['barcode_trigger'] = true;
        const action = await this.orm.call(
            this.resModel,
            this.validateMethod,
            [this.recordIds],
            { context },
        );
        const options = {
            onClose: ev => this._closeValidate(ev)
        };
        if (action && (action.res_model || action.type == "ir.actions.client")) {
            if (action.type == "ir.actions.client") {
                action.params = Object.assign(action.params || {}, options)
            }
            this.trigger("playSound");
            return this.action.doAction(action, options);
        }
        return options.onClose();
    }

    /**
     * Check if the URI was already scanned.
     * @param {String} uri
     * @returns {Boolean}
     */
    uriInCache(uri) {
        return this.uriCache.has(uri);
    }

    /**
     * Sometimes, the model receives multiple barcodes as one single string.
     * This method decomposes it into a list of barcodes.
     * @param {String} barcode
     * @returns {Array<String>}
     */
    splitBarcode(barcode) {
        // If the barcode has multiple URI, separate them.
        const matchedURI = [...barcode.matchAll(/urn:(?:[a-z0-9 -]+:){3} ?[0-9.]+/g)];
        if (matchedURI.length > 1) {
            return matchedURI.map(uri => uri[0]);
        }
        // If the barcode contains the separator, split it.
        const sepRegex = RegExp(this.config.barcode_separator_regex);
        const splitBarcodes = barcode.split(sepRegex).filter(bc => bc);
        if (splitBarcodes.length > 1) {
            return [...splitBarcodes];
        }
        return [barcode];
    }

    async processBarcode(barcode, options={}) {
        if (!barcode) {
            return; // Do nothing if no barcode given.
        }
        const { readingRFID } = options;
        const barcodes = this.splitBarcode(barcode);
        if (barcodes.length > 1 && barcode === this._currentBarcode) {
            // Scanning multiple barcodes at once can take some time and the user may be
            // tempted to scan again, thinking that the barcodes weren't scanned.
            // To avoid processing the same group of barcodes multiple times, we keep the
            // last scanned group of barcodes in memory and nothing will be done if the barcode
            // is scanned again while previous one is still in process.
            return;
        }
        this._currentBarcode = barcode;

        // Filters out already scanned URI.
        const filteredBarcodes = [];
        for (const bc of barcodes) {
            const matchedURI = bc.match(/^urn:.*$/);
            if (matchedURI && this.uriInCache(matchedURI[0])) {
                continue;
            }
            filteredBarcodes.push(bc);
        }

        if (barcodes.length > 1 && !readingRFID) {
            this.trigger("addBarcodesCountToProcess", filteredBarcodes.length)
        }
        // Parse all barcodes.
        const parsedBarcodes = [];
        for (const bc of filteredBarcodes) {
            const barcodeObject = BarcodeObject.forBarcode(bc);
            await barcodeObject.setRecords();
            parsedBarcodes.push(barcodeObject);
        }
        // Fetch all needed missing data and add them to the cache.
        await this._getMissingRecords();

        // Link parsed barcodes with missing information to the corresponding record(s).
        const validBarcodes = [];
        for (const barcodeObject of parsedBarcodes) {
            if (barcodeObject.hasMissingRecords) {
                await barcodeObject.setRecords();
                if (barcodeObject.isURN && barcodeObject.hasMissingRecords &&
                    barcodeObject.missingRecords.find(mr => mr.type === "product")) {
                    // This barcode is linked to a product we don't have => We ignore it.
                    // TODO: what to do with those barcodes ? Missing product => Barcode Lookup ?
                    // TODO: already scanned SN should be managed here too ?
                    this.trigger("updateBarcodesCountProcessed");
                    continue;
                }
            }
            validBarcodes.push(barcodeObject);
        }

        this.actionMutex.exec(async () => {
            for (const barcodeObject of validBarcodes) {
                // TODO: use already parsed barcode in `_processBarcode` instead of parse it again.
                await this._processBarcode(barcodeObject.rawValue);
                this.trigger("updateBarcodesCountProcessed");
            }
        });
        this.postProcessBarcode();
    }

    /**
     * Called after scanned barcodes were processed to do some cleanings.
     */
    postProcessBarcode() {
        this.trigger("clearBarcodesCountProcessed");
        this.notificationCache.clear();
        delete this._currentBarcode;
    }

    _getMissingRecordsParams() {
        return {
            context: { allowed_company_ids: [this._getCompanyId()], },
            forceUnrestrictedSearch: !this.parser.nomenclature.is_gs1_nomenclature,
        };
    }

    async _getMissingRecords() {
        const params = this._getMissingRecordsParams();
        await this.cache.getMissingRecords(params);
    }

    async getGs1Filters(gs1RulesData) {
        const gs1Filters = {};
        const productRule = gs1RulesData.find(bc => bc.type === "product");
        if (productRule) {
            let product = await this.cache.getRecordByBarcode(productRule.value, "product.product");
            if (!product) {
                const packaging = await this.cache.getRecordByBarcode(productRule.value, "product.packaging");
                if (packaging) {
                    product = this.cache.getRecord("product.product", packaging.product_id);
                }
            }
            if (product) {
                gs1Filters["stock.lot"] = { product_id: product.id };
            }
        }
        return gs1Filters;
    }

    // --------------------------------------------------------------------------
    // Private
    // --------------------------------------------------------------------------

    _canOverrideTrackingNumber(line, newLotName) {
        const lineLotName = line.lot_name || line.lot_id?.name;
        return !newLotName || !lineLotName || newLotName === lineLotName;
    }

    _checkBarcode(barcodeData) {
        return true;
    }

    async _closeValidate(ev) {
        if (ev === undefined) {
            // If all is OK, displays a notification and goes back to the previous page.
            this.notification(this.validateMessage, { type: "success" });
            this.trigger('history-back');
        }
    }

    _convertDataToFieldsParams(args) {
        throw new Error('Not Implemented');
    }

    createNewLine(params) {
        return this._createNewLine(params);
    }

    /**
     * Creates a new line with passed parameters, adds it to the barcode app and
     * to the list of lines to save, then refresh the page.
     *
     * @param {Object} params
     * @param {Object} params.copyOf line to copy fields' value from
     * @param {Object} params.fieldsParams fields' value to override
     * @returns {Object} the newly created line
     */
    async _createNewLine(params) {
        if (params.fieldsParams && params.fieldsParams.uom && params.fieldsParams.product_id) {
            let productUOM = this.cache.getRecord('uom.uom', params.fieldsParams.product_id.uom_id);
            let paramsUOM = params.fieldsParams.uom;
            if (paramsUOM.category_id !== productUOM.category_id) {
                // Not the same UoM's category -> Can't be converted.
                const message = _t(
                    "Scanned quantity uses %(unit)s as its Unit of Measure (UoM), but it is not compatible with the product's UoM (%(productUnit)s).",
                    { unit: paramsUOM.name, productUnit: productUOM.name }
                );
                this.notification(message, { title: _t("Wrong Unit of Measure"), type: "danger" });
                return false;
            }
        }
        const newLine = Object.assign(
            {},
            params.copyOf,
            this._getNewLineDefaultValues(params.fieldsParams)
        );
        const previousIndex = (params.copyOf || this.selectedLine || {}).sortIndex;
        if (previousIndex !== undefined) {
            // In case we copy an existing line, we update sort index of following
            // lines to interpose new line just behind the copied line.
            const newIndex = previousIndex + 1;
            for (const line of this.currentState.lines) {
                if (line.sortIndex >= newIndex) {
                    line.sortIndex += 1;
                }
            }
            this.currentSortIndex += 1;
            newLine.sortIndex = newIndex;
        } else {
            newLine.sortIndex = this._getLineIndex();
        }
        await this.updateLine(newLine, params.fieldsParams);
        this.currentState.lines.push(newLine);
        return newLine;
    }

    async deleteLine(line) {
        if (!line.id) {
            // The line doesn't exist in the DB yet => Delete it only in the frontend.
            const index = this.currentState.lines.findIndex(l => l.virtual_id === line.virtual_id);
            this.currentState.lines.splice(index, 1);
            this.linesToSave = this.linesToSave.filter(vId => vId !== line.virtual_id);
        } else {
            await this.save();
            await this.orm.call(this.lineModel, this.deleteLineMethod, [line.id]);
            this.trigger('refresh');
        }
    }

    _shouldCreateLineOnExceed(line) {
        return true;
    }

    _defaultLocation() {
        const lastScannedLocation = this.lastScanned.sourceLocation;
        return lastScannedLocation || Object.values(this.cache.dbIdCache['stock.location'])[0];
    }

    _defaultDestLocation() {
        return undefined;
    }

    _getCommands() {
        const commands = {'OCDMENU': this._goToMainMenu.bind(this)};
        if (!this.isDone) {
            commands['OBTVALI'] = () => {
                if (this.canBeValidate) {
                    this.validate();
                } else {
                    this.trigger("playSound", "error");
                }
            };
        }
        return commands;
    }

    _getLineIndex() {
        const sortIndex = this.currentSortIndex;
        this.currentSortIndex++;
        return sortIndex;
    }

    _getModelRecord() {
        return false;
    }

    _getNewLineDefaultValues(fieldsParams) {
        return {
            id: (fieldsParams && fieldsParams.id) || false,
            virtual_id: this._uniqueVirtualId,
            location_id: this._defaultLocation(),
            package_id: false,
        };
    }

    _getNewLineDefaultContext() {
        throw new Error('Not Implemented');
    }

    _getParentLine(line) {
        return line && line.parentLine;
    }

    _getFieldToWrite() {
        throw new Error('Not Implemented');
    }

    _fieldToValue(fieldValue) {
        return typeof fieldValue === 'object' ? fieldValue.id : fieldValue;
    }

    _getSaveLineCommand() {
        const commands = [];
        const fields = this._getFieldToWrite();
        for (const virtualId of this.linesToSave) {
            const line = this.currentState.lines.find(l => l.virtual_id === virtualId);
            if (line.id) { // Update an existing line.
                const initialLine = this.initialState.lines.find(l => l.virtual_id === line.virtual_id);
                const changedValues = {};
                let somethingToSave = false;
                for (const field of fields) {
                    const fieldValue = line[field];
                    const initialValue = initialLine[field];
                    if (fieldValue !== undefined && (
                        (['boolean', 'number', 'string'].includes(typeof fieldValue) && fieldValue !== initialValue) ||
                        (typeof fieldValue === 'object' && fieldValue.id !== initialValue.id)
                    )) {
                        changedValues[field] = this._fieldToValue(fieldValue);
                        somethingToSave = true;
                    }
                }
                if (somethingToSave) {
                    commands.push([1, line.id, changedValues]);
                }
            } else { // Create a new line.
                commands.push([0, 0, this._createCommandVals(line)]);
            }
        }
        return commands;
    }

    _getSaveCommand() {
        throw new Error('Not Implemented');
    }

    _groupSublines(sublines, ids, virtual_ids, _qtyDemand, _qtyDone) {
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
        });
        for (const subline of sublines) {
            subline.parentLine = groupedLine;
        }
        return groupedLine;
    }

    async _goToMainMenu() {
        await this.save();
        this.action.doAction('stock_barcode.stock_barcode_action_main_menu', {
            clearBreadcrumbs: true,
        });
    }

    _createLinesState() {
        /* Basic lines structure */
        throw new Error('Not Implemented');
    }

    /**
     * Says if a tracked line can be incremented even if there is no tracking number on it.
     *
     * @returns {boolean}
     */
    _incrementTrackedLine() {
        return false;
    }

    _lineIsNotComplete(line) {
        throw new Error('Not Implemented');
    }

    /**
     * Keeps the track of a modified lines to save them later.
     *
     * @param {Object} line
     */
    _markLineAsDirty(line) {
        this.scannedLinesVirtualId.push(line.virtual_id);
        if (!this.linesToSave.includes(line.virtual_id)) {
            this.linesToSave.push(line.virtual_id);
        }
    }

    _moveEntirePackage() {
        return false;
    }

    /**
     * Will parse the given barcode according to the used nomenclature and return
     * the retrieved data as an object.
     *
     * @param {string} barcode
     * @param {Object} filters For some models, different records can have the same barcode
     *      (`stock.lot` for example). In this case, these filters can help to get only
     *      the wanted record by filtering by record's field's value.
     * @returns {Object} Containing following data:
     *      - {string} barcode: the scanned barcode
     *      - {boolean} match: true if the barcode match an existing record
     *      - {Object} data type: an object for each type of data/record corresponding to the
     *                 barcode. It could be 'action', 'location', 'product', ...
     */
    async _parseBarcode(barcode, filters) {
        const result = {
            barcode,
            match: false,
        };
        if (this.commands[barcode]) {
            result.action = this.commands[barcode];
            result.match = true;
            return result;
        }
        let parsedBarcode;
        try {
            parsedBarcode = this.parser.parse_barcode(barcode);
        } catch (err) {
            // The barcode can't be parsed but the error is caught to fallback
            // on the classic way to handle barcodes.
            console.log(`%cWarning: error about ${barcode}`, 'text-weight: bold;');
            console.log(err.message);
        }
        if (parsedBarcode) {
            if (parsedBarcode.length) { // With the GS1 nomenclature, the parsed result is a list.
                const gs1Filters = await this.getGs1Filters(parsedBarcode);
                for (const data of parsedBarcode) {
                    if (data.type === "lot" && result.product?.tracking === "none") {
                        continue; // For product not tracked, we don't care about the lot.
                    }
                    const parsedData = await this._processGs1Data(data, gs1Filters);
                    Object.assign(result, parsedData);
                }
                if(result.match) {
                    return result;
                }
            } else if (parsedBarcode.type === 'weight') {
                result.weight = parsedBarcode;
                result.match = true;
                barcode = parsedBarcode.base_code;
            } else if (parsedBarcode.type === 'price') {
                result.match = true;
                barcode = parsedBarcode.base_code;
            } else if (parsedBarcode.type === 'product' && parsedBarcode.code !== barcode) {
                // The scanned barcode should match a product but was either an
                // alias, either converted from UPC-A to EAN-13 (or vice versa.)
                barcode = parsedBarcode.code;
                if (this.commands[barcode]) {
                    result.action = this.commands[barcode];
                    result.match = true;
                    return result; // Simple barcode, no more information to retrieve.
                }
            }
        }
        const fetchedRecord = await this._fetchRecordFromTheCache(barcode, filters, result);
        return Object.assign(result, fetchedRecord);
    }

    async _fetchRecordFromTheCache(barcode, filters, data) {
        const result = data || { barcode, match: false };
        const recordByData = await this.cache.getRecordByBarcode(barcode, false, { filters });
        if (recordByData.size > 1) {
            const message = _t(
                "Barcode scan is ambiguous with several model: %s. Use the most likely.",
                Array.from(recordByData.keys())
            );
            this.notification(message, { type: "warning" });
        }

        if (this.groups.group_stock_multi_locations) {
            const location = recordByData.get('stock.location');
            if (location) {
                this._setLocationFromBarcode(result, location);
                result.match = true;
            }
        }

        if (this.groups.group_tracking_lot) {
            const packageType = recordByData.get('stock.package.type');
            const stockPackage = recordByData.get('stock.quant.package');
            if (stockPackage) {
                // TODO: should take packages only in current (sub)location.
                result.package = stockPackage;
                result.match = true;
            }
            if (packageType) {
                result.packageType = packageType;
                result.match = true;
            }
        }

        const product = recordByData.get('product.product');
        if (product) {
            result.product = product;
            result.match = true;
        }
        if (this.groups.group_stock_packaging) {
            const packaging = recordByData.get('product.packaging');
            if (packaging) {
                result.match = true;
                result.packaging = packaging;
            }
        }
        if (this.useExistingLots) {
            const lot = recordByData.get('stock.lot');
            if (lot) {
                result.lot = lot;
                result.match = true;
            }
        }

        if (!result.match && this.packageTypes.length) {
            // If no match, check if the barcode begins with a package type's barcode.
            for (const [packageTypeBarcode, packageTypeId] of this.packageTypes) {
                if (barcode.indexOf(packageTypeBarcode) === 0) {
                    result.packageType = await this.cache.getRecord('stock.package.type', packageTypeId);
                    result.packageName = barcode;
                    result.match = true;
                    break;
                }
            }
        }
        return result;
    }

    async print(action, method) {
        await this.save();
        const options = this._getPrintOptions();
        if (options.warning) {
            return this.notification(options.warning, { type: "warning" });
        }
        if (!action && method) {
            action = await this.orm.call(
                this.resModel,
                method,
                [[this.resId]]
            );
        }
        this.action.doAction(action, options);
    }

    async _processGs1Data(data, filters) {
        const result = {};
        const { rule, type, value } = data;
        if (["location", "location_dest"].includes(type)) {
            const location = await this.cache.getRecordByBarcode(value, 'stock.location');
            if (!location) {
                return;
            } else {
                result.location = location;
                result.match = true;
            }
        } else if (type === "lot") {
            if (this.useExistingLots) {
                result.lot = await this.cache.getRecordByBarcode(value, 'stock.lot', { filters });
            }
            if (!result.lot) { // No existing lot found, set a lot name.
                result.lotName = value;
            }
            if (result.lot || result.lotName) {
                result.match = true;
            }
        } else if (type === "package") {
            const stockPackage = await this.cache.getRecordByBarcode(value, 'stock.quant.package');
            if (stockPackage) {
                result.package = stockPackage;
            } else {
                // Will be used to force package's name when put in pack.
                result.packageName = value;
            }
            result.match = true;
        } else if (type === "package_type") {
            const packageType = await this.cache.getRecordByBarcode(value, 'stock.package.type');
            if (packageType) {
                result.packageType = packageType;
                result.match = true;
            } else {
                const message = _t("An unexisting package type was scanned. This part of the barcode can't be processed.");
                this.notification(message, { type: "warning" });
            }
        } else if (type === "product") {
            const product = await this.cache.getRecordByBarcode(value, 'product.product');
            if (product) {
                result.product = product;
                result.match = true;
            } else if (this.groups.group_stock_packaging) {
                const packaging = await this.cache.getRecordByBarcode(value, 'product.packaging');
                if (packaging) {
                    result.packaging = packaging;
                    result.match = true;
                }
            }
        } else if (type === "quantity") {
            result.quantity = value;
            // The quantity is usually associated to an UoM, but we
            // ignore this info if the UoM setting is disabled.
            if (this.groups.group_uom && rule?.associated_uom_id) {
                result.uom = await this.cache.getRecord('uom.uom', rule.associated_uom_id);
            }
            result.match = result.quantity ? true : false;
        }
        return result;
    }

    /**
     * Starts by parse the barcode and then process each type of barcode data.
     *
     * @param {string} barcode
     * @returns {Promise}
     */
    async _processBarcode(barcode) {
        let barcodeData = {};
        let currentLine = false;
        // Creates a filter if needed, which can help to get the right record
        // when multiple records have the same model and barcode.
        const filters = {};
        if (this.selectedLine && this.selectedLine.product_id.tracking !== 'none') {
            filters['stock.lot'] = {
                product_id: this.selectedLine.product_id.id,
            };
        }
        // Constrain DB reads to records which belong to the company defined on the open operation
        filters['all'] = {
            company_id: [false].concat(this._getCompanyId() || []),
        };
        try {
            barcodeData = await this._parseBarcode(barcode, filters);
            if (this._shouldSearchForAnotherLot(barcodeData, filters)) {
                // Retry to parse the barcode without filters in case it matches an existing
                // record that can't be found because of the filters
                const lot = await this.cache.getRecordByBarcode(barcode, 'stock.lot');
                if (lot) {
                    Object.assign(barcodeData, { lot, match: true });
                }
            }
        } catch (parseErrorMessage) {
            barcodeData.error = parseErrorMessage;
        }

        // Keep in memory every scans.
        this.scanHistory.unshift(barcodeData);

        if (barcodeData.match) { // Makes flash the screen if the scanned barcode was recognized.
            this.trigger('flash');
        }

        // Process each data in order, starting with non-ambiguous data type.
        if (barcodeData.action) { // As action is always a single data, call it and do nothing else.
            return await barcodeData.action();
        }

        if (barcodeData.packaging) {
            Object.assign(barcodeData, this._retrievePackagingData(barcodeData));
        }

        // Depending of the configuration, the user can be forced to scan a specific barcode type.
        const check = this._checkBarcode(barcodeData);
        if (check.error) {
            return this.notification(check.message, { title: check.title, type: "danger" });
        }

        if (barcodeData.product) { // Remembers the product if a (packaging) product was scanned.
            this.lastScanned.product = barcodeData.product;
        }

        if (barcodeData.lot && !barcodeData.product) {
            Object.assign(barcodeData, this._retrieveTrackingNumberInfo(barcodeData.lot));
        }

        await this._processLocation(barcodeData);
        await this._processPackage(barcodeData);
        if (barcodeData.stopped) {
            // TODO: Sometime we want to stop here instead of keeping doing thing,
            // but it's a little hacky, it could be better to don't have to do that.
            return;
        }

        if (barcodeData.weight) { // Convert the weight into quantity.
            barcodeData.quantity = barcodeData.weight.value;
        }

        // If no product found, take the one from last scanned line if possible.
        if (!barcodeData.product) {
            if (barcodeData.quantity) {
                currentLine = this.selectedLine || this.lastScannedLine;
            } else if (this.selectedLine && this.selectedLine.product_id.tracking !== 'none') {
                currentLine = this.selectedLine;
            } else if (this.lastScannedLine && this.lastScannedLine.product_id.tracking !== 'none') {
                currentLine = this.lastScannedLine;
            }
            if (currentLine) { // If we can, get the product from the previous line.
                const previousProduct = currentLine.product_id;
                // If the current product is tracked and the barcode doesn't fit
                // anything else, we assume it's a new lot/serial number.
                if (previousProduct.tracking !== 'none' &&
                    !barcodeData.match && this.canCreateNewLot) {
                    this.trigger('flash');
                    barcodeData.lotName = barcode;
                    barcodeData.product = previousProduct;
                }
                if (barcodeData.lot || barcodeData.lotName ||
                    barcodeData.quantity) {
                    barcodeData.product = previousProduct;
                }
            }
        }
        let { product } = barcodeData;
        if (!product && barcodeData.match && this.parser.nomenclature.is_gs1_nomenclature) {
            // Special case where something was found using the GS1 nomenclature but no product is
            // used (eg.: a product's barcode can be read as a lot is starting with 21).
            // In such case, tries to find a record with the barcode by by-passing the parser.
            barcodeData = await this._fetchRecordFromTheCache(barcode, filters);
            if (barcodeData.packaging) {
                Object.assign(barcodeData, this._retrievePackagingData(barcodeData));
            } else if (barcodeData.lot) {
                Object.assign(barcodeData, this._retrieveTrackingNumberInfo(barcodeData.lot));
            }
            if (barcodeData.product) {
                product = barcodeData.product;
            } else if (barcodeData.match) {
                await this._processPackage(barcodeData);
                if (barcodeData.stopped) {
                    return;
                }
            }
        }
        if (!product) { // Product is mandatory, if no product, raises a warning.
            return this.noProductToast(barcodeData);
        } else if (barcodeData.lot && barcodeData.lot.product_id !== product.id) {
            delete barcodeData.lot; // The product was scanned alongside another product's lot.
        }
        if (barcodeData.weight) { // the encoded weight is based on the product's UoM
            barcodeData.uom = this.cache.getRecord('uom.uom', product.uom_id);
        }

        // Searches and selects a line if needed.
        if (!currentLine || this._shouldSearchForAnotherLine(currentLine, barcodeData)) {
            currentLine = this._findLine(barcodeData);
        }

        // Default quantity set to 1 by default if the product is untracked or
        // if there is a scanned tracking number.
        if (product.tracking === 'none' || barcodeData.lot || barcodeData.lotName || this._incrementTrackedLine()) {
            const hasUnassignedQty = currentLine && currentLine.qty_done && !currentLine.lot_id && !currentLine.lot_name;
            const isTrackingNumber = barcodeData.lot || barcodeData.lotName;
            const defaultQuantity = isTrackingNumber && hasUnassignedQty ? 0 : 1;
            barcodeData.quantity = barcodeData.quantity || defaultQuantity;
            if (product.tracking === 'serial' && barcodeData.quantity > 1 && (barcodeData.lot || barcodeData.lotName)) {
                barcodeData.quantity = 1;
                this.notification(
                    _t(`A product tracked by serial numbers can't have multiple quantities for the same serial number.`),
                    { type: 'danger' }
                );
            }
        }

        if ((barcodeData.lotName || barcodeData.lot) && product) {
            const lotName = barcodeData.lotName || barcodeData.lot.name;
            for (const line of this.currentState.lines) {
                if (line.product_id.id !== product.id) {
                    continue; // The same SN can be scanned for different product.
                }
                if (line.product_id.tracking === "serial" && this.getQtyDone(line) !== 0 &&
                    this.getlotName(line) === lotName) {
                    return this.notification(
                        _t("The scanned serial number %s is already used.", lotName),
                        { type: 'danger' }
                    );
                }
            }
            // Prefills `owner_id` and `package_id` if possible.
            const prefilledOwner = (!currentLine || (currentLine && !currentLine.owner_id)) && this.groups.group_tracking_owner && !barcodeData.owner;
            const prefilledPackage = (!currentLine || (currentLine && !currentLine.package_id)) && this.groups.group_tracking_lot && !barcodeData.package;
            if (this.useExistingLots && (prefilledOwner || prefilledPackage)) {
                const lotId = (barcodeData.lot && barcodeData.lot.id) || (currentLine && currentLine.lot_id && currentLine.lot_id.id) || false;
                const locationId = (currentLine && currentLine.location_id && currentLine.location_id.id) || false;
                const params = {
                    lot_id: lotId,
                    lot_name: (!lotId && barcodeData.lotName) || false,
                };
                let quants = await this.cache.getQuants(product, locationId, params);
                if (quants.length && quants.length > 1 && (prefilledPackage || prefilledOwner)) {
                    // If we have multiple matching quants and we use package and/or consigment,
                    // give priority to the quants with a package or an owner.
                    const filteredQuants = quants.filter((quant) => {
                        return quant.package_id || quant.owner_id;
                    });
                    quants = filteredQuants.length ? filteredQuants : quants;
                }
                if (quants && quants.length === 1) {
                    const quant = quants[0];
                    if (prefilledPackage && quant.package_id) {
                        barcodeData.package = this.cache.getRecord("stock.quant.package", quant.package_id);
                    }
                    if (prefilledOwner && quant.owner_id) {
                        barcodeData.owner = this.cache.getRecord("res.partner", quant.owner_id);
                    }
                }
            }
        }

        // Updates or creates a line based on barcode data.
        if (currentLine) { // If line found, can it be incremented ?
            let exceedingQuantity = 0;
            if (product.tracking !== 'serial' && barcodeData.uom && barcodeData.uom.category_id == currentLine.product_uom_id.category_id) {
                // convert to current line's uom
                barcodeData.quantity = (barcodeData.quantity / barcodeData.uom.factor) * currentLine.product_uom_id.factor;
                barcodeData.uom = currentLine.product_uom_id;
            }
            // Checks the quantity doesn't exceed the line's remaining quantity.
            if (currentLine.reserved_uom_qty && product.tracking === 'none') {
                const remainingQty = currentLine.reserved_uom_qty - currentLine.qty_done;
                if (barcodeData.quantity > remainingQty && this._shouldCreateLineOnExceed(currentLine)) {
                    // In this case, lowers the increment quantity and keeps
                    // the excess quantity to create a new line.
                    exceedingQuantity = barcodeData.quantity - remainingQty;
                    barcodeData.quantity = remainingQty;
                }
            }
            if (barcodeData.quantity > 0 || barcodeData.lot || barcodeData.lotName) {
                const fieldsParams = this._convertDataToFieldsParams(barcodeData);
                if (barcodeData.uom) {
                    fieldsParams.uom = barcodeData.uom;
                }
                await this.updateLine(currentLine, fieldsParams);
                this.trigger("playSound", "success");
            }
            if (exceedingQuantity) { // Creates a new line for the excess quantity.
                barcodeData.quantity = exceedingQuantity;
                const fieldsParams = this._convertDataToFieldsParams(barcodeData);
                if (barcodeData.uom) {
                    fieldsParams.uom = barcodeData.uom;
                }
                currentLine = await this._createNewLine({
                    copyOf: currentLine,
                    fieldsParams,
                });
            }
        } else { // No line found, so creates a new one.
            const fieldsParams = this._convertDataToFieldsParams(barcodeData);
            if (barcodeData.uom) {
                fieldsParams.uom = barcodeData.uom;
            }
            if (this.createSingleLinesForPackaging(barcodeData)) {
                for (let lineCount = 0; lineCount < barcodeData.packaging.qty; lineCount++) {
                    currentLine = await this.createNewLine({fieldsParams});
                }
            } else {
                currentLine = await this.createNewLine({fieldsParams});
            }
            if(currentLine){
                this.trigger("playSound", "success");
            }
        }

        // And finally, if the scanned barcode modified a line, selects this line.
        if (currentLine) {
            this._selectLine(currentLine);
        }

        const matchedURI = barcode.match(/^urn:.*$/);
        if (matchedURI) {
            // If the process goes right and the scanned barcode is an URI, add
            // it to the cache to avoid scanning it a second time.
            this.uriCache.add(barcode);
        }
        this.trigger('update');
    }

    noProductToast(barcodeData) {
        if (!barcodeData.error) {
            if (this.groups.group_tracking_lot) {
                barcodeData.error = _t("You are expected to scan one or more products or a package available at the picking location");
            } else {
                barcodeData.error = _t("This product doesn't exist.");
            }
        }
        return this.notification(barcodeData.error, { type: "danger" });
    }

    async _processLocation(barcodeData) {
        if (barcodeData.location) {
            await this._processLocationSource(barcodeData);
            this.trigger("playSound", "success");
            this.trigger('update');
        }
    }

    async _processLocationSource(barcodeData) {
        this.location = barcodeData.location;
        barcodeData.stopped = true;
        // Unselects the line.
        this.selectedLineVirtualId = false;
        this.lastScanned.packageId = false;
    }

    async _processPackage(barcodeData) {
        throw new Error('Not Implemented');
    }

    /**
     * This method cleans the barcode in case the parser use the GS1 nomenclature, removing the
     * parentheses and the extra spaces (helping for human readability but not valid).
     * E.g.: (01) 00001234567895 (10) lot-abc -> 0100001234567895\x1D10lot-abc
     *
     * @param {string} barcode
     * @returns {string} barcode
     */
    cleanBarcode (barcode) {
        if (this.parser.nomenclature.is_gs1_nomenclature) {
            barcode = barcode.replace(/[( ]([0-9]+)[)]/g, `${FNC1_CHAR}$1`);
            if (barcode[0] === FNC1_CHAR) {
                barcode = barcode.slice(1, barcode.length);
            }
        }
        return barcode;
    }

    lineCanBeSelected() {
        return true;
    }

    lineCanBeEdited() {
        return true;
    }

    /**
     * Check if a given line can be taken depending of the current location (if no current location,
     * it will always be true).
     * @param {Object} line
     * @returns {Boolean}
     */
    lineCanBeTakenFromTheCurrentLocation(line) {
        return this.lineIsInTheCurrentLocation(line);
    }

    lineIsInTheCurrentLocation(line) {
        return Boolean(
            !this.groups.group_stock_multi_locations ||
            !this.lastScanned.sourceLocation || // No current location so we don't care.
            this.lastScanned.sourceLocation.id == line.location_id.id // Line at the right location.
        );
    }

    _retrievePackagingData(barcodeData) {
        const product = this.cache.getRecord('product.product', barcodeData.packaging.product_id);
        const uom = this.cache.getRecord('uom.uom', product.uom_id);
        let quantity = "quantity" in barcodeData ? barcodeData.quantity : 1;
        if (barcodeData.uom && barcodeData.uom.category_id !== uom.category_id) {
            // In case the scanned quantity uses an UoM not compatible with the
            // product UoM, we drop it and uses the packaging quantity instead.
            quantity = barcodeData.packaging.qty
        } else {
            // Otherwise, multiply the scanned quantity (or 1 by default) by the package quantity.
            quantity *= barcodeData.packaging.qty;
        }
        return { product, quantity, uom };
    }

    _retrieveTrackingNumberInfo(lot) {
        return { product: this.cache.getRecord('product.product', lot.product_id) };
    }

    _selectLine(line) {
        const virtualId = line.virtual_id;
        if (this.selectedLineVirtualId === virtualId) {
            return; // Don't select the line if it's already selected.
        }
        this.selectedLineVirtualId = virtualId;
        this.lastScanned.destLocation = false;
    }

    _setLocationFromBarcode(result, location) {
        result.location = location;
        return result;
    }

    _sortingMethod(l1, l2) {
        // Sort by source location.
        const sourceLocation1 = l1.location_id.display_name;
        const sourceLocation2 = l2.location_id.display_name;
        if (sourceLocation1 < sourceLocation2) {
            return -1;
        } else if (sourceLocation1 > sourceLocation2) {
            return 1;
        }
        // Sort by (source) package.
        const package1 = l1.package_id.name;
        const package2 = l2.package_id.name;
        if (package1 < package2) {
            return -1;
        } else if (package1 > package2) {
            return 1;
        }
        // Sort by destination location.
        if (l1.location_dest_id && l2.location_dest_id) {
            const destinationLocation1 = l1.location_dest_id.display_name;
            const destinationLocation2 = l2.location_dest_id.display_name;
            if (destinationLocation1 < destinationLocation2) {
                return -1;
            } else if (destinationLocation1 > destinationLocation2) {
                return 1;
            }
        }
        // Sort by result package.
        if (l1.result_package_id && l2.result_package_id) {
            const resultPackage1 = l1.result_package_id.name;
            const resultPackage2 = l2.result_package_id.name;
            if (resultPackage1 < resultPackage2) {
                return -1;
            } else if (resultPackage1 > resultPackage2) {
                return 1;
            }
        }
        // Sort by product's category.
        const categ1 = l1.product_category_name;
        const categ2 = l2.product_category_name;
        if (categ1 < categ2) {
            return -1;
        } else if (categ1 > categ2) {
            return 1;
        }
        // Sort by product's display name.
        const product1 = l1.product_id.display_name;
        const product2 = l2.product_id.display_name;
        if (product1 < product2) {
            return -1;
        } else if (product1 > product2) {
            return 1;
        }
        return 0;
    }

    /**
     * Sorts the lines to have new lines always on top and complete lines always on the bottom.
     *
     * @param {Array<Object>} lines
     * @returns {Array<Object>}
     */
    _sortLine(lines) {
        return lines.sort((l1, l2) => {
            return l1.sortIndex > l2.sortIndex ? 1 : -1;
        });
    }

    _findLine(barcodeData) {
        let foundLine = false;
        const {lot, lotName, product} = barcodeData;
        const quantPackage = barcodeData.package;
        const dataLotName = lotName || (lot && lot.name) || false;
        let pageLines = [...this.pageLines]
        // If a line is selected, unshift it to the first position to start the search by it
        if (this.selectedLineVirtualId) {
            const selectedLineIndex = pageLines.findIndex(line => line.virtual_id == this.selectedLineVirtualId);
            if (selectedLineIndex > -1) {
                pageLines.splice(selectedLineIndex, 1);
                pageLines.unshift(this.pageLines[selectedLineIndex]);
            }
        }
        for (const line of pageLines) {
            const lineLotName = this.getlotName(line);
            if (line.product_id.id !== product.id) {
                continue; // Not the same product.
            }
            if (quantPackage && (!line.package_id || line.package_id.id !== quantPackage.id)) {
                continue; // Not the expected package.
            }
            if (line.product_id.tracking !== "none" && !this._canOverrideTrackingNumber(line, dataLotName)) {
                continue; // Not the same lot.
            }
            if (line.product_id.tracking === 'serial') {
                if (this.getQtyDone(line) >= 1 && lineLotName) {
                    continue; // Line tracked by serial numbers with quantity & SN.
                } else if (dataLotName && this.getQtyDone(line) > 1) {
                    continue; // Can't add a SN on a line where multiple qty. was previously added.
                }
            }
            if ((
                    !dataLotName || !lineLotName || dataLotName !== lineLotName
                ) && (
                    line.qty_done && line.qty_done >= line.reserved_uom_qty &&
                    (line.product_id.tracking === "none" || lineLotName) &&
                    line.id && (!this.selectedLine || line.virtual_id != this.selectedLine.virtual_id)
                )) {
                    // Has enough quantity (and another lot is set if the line's product is tracked)
                    // and the line wasn't explicitly selected.
                    continue;
            }
            if (this._lineCannotBeTaken(line)) {
                continue;
            }
            if (this._lineIsNotComplete(line)) {
                if (this.lineCanBeTakenFromTheCurrentLocation(line)) {
                    // Found a uncompleted compatible line, stop searching if it has the same location
                    // than the scanned one (or if no location was scanned).
                    foundLine = line;
                    if ((this.lineIsInTheCurrentLocation(line)) &&
                        (line.product_id.tracking === 'none' || !dataLotName || dataLotName === lineLotName)) {
                        // In case of tracked product, stop searching only if no
                        // LN/SN was scanned or if it's the same.
                        break;
                    }
                } else if (this.needSourceConfirmation && foundLine && !this._lineIsNotComplete(foundLine)) {
                    // Found a empty line in another location, we should take it but depending of
                    // the config, maybe we can't (location should be confirmed first).
                    // That said, we already found another line but if it's completed, forget we
                    // found it to avoid to create a new line in the current location because it's
                    // basicaly the same than increment the other line found in another location.
                    foundLine = false;
                    continue;
                }
            }
            // If all the previous checks were passed, the line can be considered
            // as the found line. That said, if another line was already found,
            // it can be tricky to know which one we want to prioritize.
            if (!foundLine) {
                // The line matches but there could be a better candidate, so keep searching.
                // If multiple lines can match, prioritises the one at the right location (if a
                // location source was previously selected) or the selected one if relevant.
                const currentLocationId = this.lastScanned.sourceLocation && this.lastScanned.sourceLocation.id;
                if (this.selectedLine && this.selectedLine.virtual_id === line.virtual_id && (
                    !currentLocationId || !foundLine || foundLine.location_id.id != currentLocationId)) {
                    foundLine = this.lineCanBeTakenFromTheCurrentLocation(line) ? line : foundLine;
                } else if (!foundLine || (currentLocationId &&
                        foundLine.location_id.id != currentLocationId &&
                        line.location_id.id == currentLocationId)) {
                    foundLine = this.lineCanBeTakenFromTheCurrentLocation(line) ? line : foundLine;
                }
            } else if (this._lineIsNotComplete(foundLine)) {
                // If previous line is not completed, no reason to prioritize the current one.
                continue;
            } else if (this._lineIsNotComplete(line)) {
                // If previous line is completed and current one is not, prioritize the current one.
                foundLine = line;
            } else if (this.lineIsSelected(line) ||
                (!this.lineIsSelected(foundLine) && this.lineBelongsToSelectedLine(line))
            ) {
                // If both previous found line and current line are completed, prioritize the
                // current one only if it's the selected line (or on of its sublines.)
                foundLine = line;
            }
        }
        return foundLine;
    }

    lineBelongsToSelectedLine(line) {
        if (!this.selectedLine) {
            return false;
        }
        const selectedGroupedLine = this._getParentLine(this.selectedLine);
        return selectedGroupedLine && selectedGroupedLine.virtual_ids.includes(line.virtual_id);
    }

    /**
     * Intended to be used only by `_findLine`.
     * Depending of the model, they can have additional conditions to know if a
     * line can be took when a barcode is scanned. This method is meant to be overriden.
     * @param {Object} _line
     * @returns {Boolean}
     */
    _lineCannotBeTaken(line) {
        return !this.lineCanBeTakenFromTheCurrentLocation(line);
    }

    lineIsSelected(line) {
        return (line.dummy_id || line.virtual_id) === this.selectedLineVirtualId;
    }

    _shouldSearchForAnotherLot(barcodeData, filters) {
        return !barcodeData.match && filters['stock.lot'] &&
            !this.canCreateNewLot && this.useExistingLots
    }

    _shouldSearchForAnotherLine(line, barcodeData) {
        if (line.product_id.id !== barcodeData.product.id) {
            return true;
        }
        if (barcodeData.product.tracking === 'serial' && this.getQtyDone(line) > 0) {
            return true;
        }
        const {lot, lotName} = barcodeData;
        const dataLotName = lotName || (lot && lot.name) || false;
        const lineLotName = this.getlotName(line);
        if (dataLotName && lineLotName && dataLotName !== lineLotName) {
            return true;
        }
        const parentLine = this._getParentLine(line);
        // If the line is a part of a group, we check if the group is fulfilled.
        const currentLine = parentLine || line;
        return this.getQtyDone(currentLine) >= this.getQtyDemand(currentLine);
    }

    get _uniqueVirtualId() {
        this._lastVirtualId = this._lastVirtualId || 0;
        return ++this._lastVirtualId;
    }

    _updateLineQty(line, qty) {
        throw new Error('Not Implemented');
    }

    _updateLotName(line, lotName) {
        throw new Error('Not Implemented');
    }

    _getName() {
        return this.cache.getRecord(this.resModel, this.resId).name;
    }

    // Response -> UI State
    _createState() {
        this.record = this._getModelRecord();
        const lines = this._createLinesState();
        // Sorts the lines following some criterea and then assign an index for the sort (so they keep the same place).
        lines.sort(this._sortingMethod.bind(this));
        for (const line of lines) {
            line.sortIndex = this._getLineIndex();
        }
        this.initialState = { lines };
        this.currentState = JSON.parse(JSON.stringify(this.initialState)); // Deep copy
        this.groupLines();
    }

    _getPrintOptions() {
        return {};
    }

    zeroQtyClass(_line) {
        return "text-muted";
    }

    _getCompanyId() {
        throw new Error('Not Implemented');
    }

    _onExit() {
        return;
    }
}
