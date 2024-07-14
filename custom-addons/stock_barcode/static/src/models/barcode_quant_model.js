/** @odoo-module **/

import BarcodeModel from '@stock_barcode/models/barcode_model';
import { _t } from "@web/core/l10n/translation";

export default class BarcodeQuantModel extends BarcodeModel {
    constructor(params) {
        super(...arguments);
        this.lineModel = this.resModel;
        this.validateMessage = _t("The inventory adjustment has been validated");
        this.validateMethod = 'action_validate';
    }

    /**
     * Validates only the quants of the current inventory page and don't close it.
     *
     * @returns {Promise}
     */
    async apply() {
        await this.save();
        const linesToApply = this.pageLines.filter(line => line.inventory_quantity_set);
        if (linesToApply.length === 0) {
            const message = _t("There is nothing to apply in this page.");
            return this.notification(message, { type: "warning" });
        }
        const action = await this.orm.call('stock.quant', 'action_validate',
            [linesToApply.map(quant => quant.id)]
        );
        const notifyAndGoAhead = res => {
            if (res && res.special) { // Do nothing if come from a discarded wizard.
                return this.trigger('refresh');
            }
            this.notification(_t("The inventory adjustment has been validated"), { type: "success" });
            this.trigger('history-back');
        };
        if (action && action.res_model) {
            return this.action.doAction(action, { onClose: notifyAndGoAhead });
        }
        notifyAndGoAhead();
    }

    get applyOn() {
        return this.pageLines.filter(line => line.inventory_quantity_set).length;
    }

    get barcodeInfo() {
        // Takes the parent line if the current line is part of a group.
        let line = this._getParentLine(this.selectedLine) || this.selectedLine;
        if (!line && this.lastScanned.packageId) {
            line = this.pageLines.find(l => l.package_id && l.package_id.id === this.lastScanned.packageId);
        }
        // Defines some messages who can appear in multiple cases.
        const messages = {
            scanProduct: {
                class: 'scan_product',
                message: _t("Scan a product"),
                icon: 'tags',
            },
            scanLot: {
                class: 'scan_lot',
                message: _t(
                    "Scan lot numbers for product %s to change their quantity",
                    line ? line.product_id.display_name : ""
                ),
                icon: 'barcode',
            },
            scanSerial: {
                class: 'scan_serial',
                message: _t(
                    "Scan serial numbers for product %s to change their quantity",
                    line ? line.product_id.display_name : ""
                ),
                icon: 'barcode',
            },
        };

        if (line) { // Message depends of the selected line's state.
            const { tracking } = line.product_id;
            const trackingNumber = (line.lot_id && line.lot_id.name) || line.lot_name;
            if (this._lineIsNotComplete(line)) {
                if (tracking !== 'none') {
                    return tracking === 'lot' ? messages.scanLot : messages.scanSerial;
                }
                return messages.scanProduct;
            } else if (tracking !== 'none' && !trackingNumber) {
                // Line's quantity is fulfilled but still waiting a tracking number.
                return tracking === 'lot' ? messages.scanLot : messages.scanSerial;
            } else { // Line's quantity is fulfilled.
                if (this.groups.group_stock_multi_locations && line.location_id.id === this.location.id) {
                    return {
                        class: 'scan_product_or_src',
                        message: _t(
                            "Scan more products in %s or scan another location",
                            this.location.display_name
                        ),
                    };
                }
                return messages.scanProduct;
            }
        }
        // No line selected, returns default message (depends if multilocation is enabled).
        if (this.groups.group_stock_multi_locations) {
            if (!this.lastScanned.sourceLocation) {
                return {
                    class: 'scan_src',
                    message: _t("Scan a location"),
                    icon: 'sign-out',
                };
            }
            return {
                class: 'scan_product_or_src',
                message: _t(
                    "Scan a product in %s or scan another location",
                    this.location.display_name
                ),
            };
        }
        return messages.scanProduct;
    }

    get displayByUnitButton () {
        return true;
    }

    get displaySetButton() {
        return true;
    }

    setData(data) {
        this.userId = data.data.user_id;
        super.setData(...arguments);
        const companies = data.data.records['res.company'];
        this.companyIds = companies.map(company => company.id);
        this.lineFormViewId = data.data.line_view_id;
    }

    get displayApplyButton() {
        return true;
    }

    getDisplayIncrementBtn(line) {
        return line.product_id.tracking !== 'serial' && this.selectedLineVirtualId &&
            line.virtual_id === this.selectedLineVirtualId;
    }

    getDisplayDecrementBtn(line) {
        return this.getDisplayIncrementBtn(line);
    }

    getQtyDone(line) {
        return line.inventory_quantity_set ? line.inventory_quantity : 0;
    }

    getQtyDemand(line) {
        return line.quantity;
    }

    getActionRefresh(newId) {
        const action = super.getActionRefresh(newId);
        action.params.res_id = this.currentState.lines.map(l => l.id);
        if (newId) {
            action.params.res_id.push(newId);
        }
        return action;
    }

    get highlightValidateButton() {
        return this.applyOn > 0 && this.applyOn === this.pageLines.length;
    }

    IsNotSet(line) {
        return !line.inventory_quantity_set;
    }

    lineIsFaulty(line) {
        return line.inventory_quantity_set && line.inventory_quantity !== line.quantity;
    }

    get printButtons() {
        return [{
            name: _t("Print Inventory"),
            class: 'o_print_inventory',
            action: 'stock.action_report_inventory',
        }];
    }

    get recordIds() {
        return this.currentState.lines.map(l => l.id);
    }

    /**
     * Marks the line as set and set its inventory quantity if it was unset, or
     * unset it if the line was already set.
     *
     * @param {Object} line
     */
    setOnHandQuantity(line) {
        if (line.product_id.tracking === 'serial') { // Special case for product tracked by SN.
            const quantity = !(line.lot_name || line.lot_id) && line.quantity || 1;
            if (line.inventory_quantity_set) {
                line.inventory_quantity = line.inventory_quantity ? 0 : quantity;
                line.inventory_quantity_set = line.inventory_quantity != quantity;
            } else {
                line.inventory_quantity = quantity;
                line.inventory_quantity_set = true;
            }
            this._markLineAsDirty(line);
        } else {
            if (line.inventory_quantity_set) {
                line.inventory_quantity = 0;
                line.inventory_quantity_set = false;
                this._markLineAsDirty(line);
            } else {
                const inventory_quantity = line.quantity - line.inventory_quantity;
                this.updateLine(line, { inventory_quantity });
                line.inventory_quantity_set = true;
            }
        }
        this.trigger('update');
    }

    updateLineQty(virtualId, qty = 1) {
        this.actionMutex.exec(() => {
            const line = this.pageLines.find(l => l.virtual_id === virtualId);
            this.updateLine(line, {inventory_quantity: qty});
            this.trigger('update');
        });
    }

    // --------------------------------------------------------------------------
    // Private
    // --------------------------------------------------------------------------

    _getCommands() {
        return Object.assign(super._getCommands(), {
            'O-BTN.apply': this.apply.bind(this),
        });
    }

    _getNewLineDefaultContext() {
        return {
            default_company_id: this.companyIds[0],
            default_location_id: this._defaultLocation().id,
            default_inventory_quantity: 1,
            default_user_id: this.userId,
            inventory_mode: true,
            display_default_code: false,
        };
    }

    _createCommandVals(line) {
        const values = {
            dummy_id: line.virtual_id,
            inventory_date: line.inventory_date,
            inventory_quantity: line.inventory_quantity,
            inventory_quantity_set: line.inventory_quantity_set,
            location_id: line.location_id,
            lot_id: line.lot_id,
            lot_name: line.lot_name,
            package_id: line.package_id,
            product_id: line.product_id,
            owner_id: line.owner_id,
            user_id: this.userId,
        };
        for (const [key, value] of Object.entries(values)) {
            values[key] = this._fieldToValue(value);
        }
        return values;
    }

    async _createNewLine(params) {
        // When creating a new line, we need to know if a quant already exists
        // for this line, and in this case, update the new line fields.
        const product = params.fieldsParams.product_id;
        if (product.detailed_type != 'product') {
            const productName = (product.default_code ? `[${product.default_code}] ` : '') + product.display_name;
            const message = _t(
                "%s can't be inventoried. Only storable products can be inventoried.",
                productName
            );
            this.notification(message, { type: "warning" });
            return false;
        }
        const domain = [
            ['location_id', '=', this.location.id],
            ['product_id', '=', product.id],
        ];
        const { lot_id, package_id } = params.fieldsParams;
        if (product.tracking !== 'none') {
            if (params.fieldsParams.lot_name) { // Search for a quant with the exact same lot.
                domain.push(['lot_id.name', '=', params.fieldsParams.lot_name]);
            } else if (params.fieldsParams.lot_id) { // Search for a quant with the exact same lot.
                domain.push(['lot_id', '=', lot_id.id || lot_id]);
            }
        }
        if (params.fieldsParams.package_id) {
            domain.push(['package_id', '=', package_id.id || package_id]);
        }
        const res = await this.orm.call( 'stock.quant', 'get_existing_quant_and_related_data', [domain]);
        this.cache.setCache(res.records);
        const quants = res.records['stock.quant'];
        if (quants.length === 1 && (
            product.tracking === 'none' || params.fieldsParams.lot_name || params.fieldsParams.lot_id)) {
            const inventory_quantity = params.fieldsParams.inventory_quantity || 1;
            params.fieldsParams = Object.assign({}, params.fieldsParams, { inventory_quantity });
        }
        let newLine = false;
        if (quants.length) { // Found existing quants: create a line for each one.
            const lineIds = this.currentState.lines.map(l => l.id);
            for (const quant of quants) {
                if (lineIds.includes(quant.id)) {
                    continue; // Don't create line for quant if there is already a line for it.
                }
                const lineParams = {
                    fieldsParams: Object.assign({}, quant, params.fieldsParams),
                };
                const newlyCreatedLine = await super._createNewLine(lineParams);
                // Keeps the first created line so that the one who will be selected.
                newLine = newLine || newlyCreatedLine;
                // If the quant already exits, we add it into the `initialState` to
                // avoid comparison issue with the `currentState` when the save occurs.
                const lineWithOriginalQuantValues = Object.assign({}, newlyCreatedLine, {
                    inventory_date: quant.inventory_date,
                    inventory_quantity: quant.inventory_quantity,
                    inventory_quantity_set: quant.inventory_quantity_set,
                    quantity: quant.quantity,
                    user_id: quant.user_id,
                });
                this.initialState.lines.push(lineWithOriginalQuantValues);
            }
        } else { // No existing quant: creates an empty new line.
            newLine = await super._createNewLine(params);
        }
        return newLine;
    }

    _convertDataToFieldsParams(args) {
        const params = {};
        const argsPackage = args.package || args.resultPackage;
        // Set the fields in `params` only if they are in `args`.
        args.quantity && (params.inventory_quantity = args.quantity);
        args.lot && (params.lot_id = args.lot);
        args.lotName && (params.lot_name = args.lotName);
        args.owner && (params.owner_id = args.owner);
        argsPackage && (params.package_id = argsPackage);
        args.product && (params.product_id = args.product);
        args.product && args.product.uom_id && (params.product_uom_id = args.product.uom_id);
        return params;
    }

    _getNewLineDefaultValues(fieldsParams) {
        const defaultValues = super._getNewLineDefaultValues(...arguments);
        Object.assign(defaultValues, {
            inventory_date: new Date().toISOString().slice(0, 10),
            inventory_quantity: 0,
            quantity: (fieldsParams && fieldsParams.quantity) || 0,
            user_id: this.userId,
        });
        // Marks the new line's quantity as set only if it's not an existing quant (no `quantity`)
        // or if it already has a counted quantity. It's to avoid tragedy if the user applies by
        // mistake the inventory adjustment after scanned a product with multiple serial/lot numbers
        if (fieldsParams.quantity === undefined || fieldsParams.inventory_quantity) {
            defaultValues.inventory_quantity_set = true;
        }
        return defaultValues
    }

    _getFieldToWrite() {
        return [
            'inventory_date',
            'inventory_quantity',
            'inventory_quantity_set',
            'user_id',
            'location_id',
            'lot_name',
            'lot_id',
            'package_id',
            'owner_id',
        ];
    }

    _getSaveCommand() {
        const commands = this._getSaveLineCommand();
        if (commands.length) {
            return {
                route: '/stock_barcode/save_barcode_data',
                params: {
                    model: this.resModel,
                    res_id: false,
                    write_field: false,
                    write_vals: commands,
                },
            };
        }
        return {};
    }

    _groupSublines(sublines, ids, virtual_ids, qtyDemand, qtyDone) {
        return Object.assign(super._groupSublines(...arguments), {
            inventory_quantity: qtyDone,
            quantity: qtyDemand,
        });
    }

    _lineIsNotComplete(line) {
        return line.inventory_quantity === 0;
    }

    async _processPackage(barcodeData) {
        const { packageType, packageName } = barcodeData;
        let recPackage = barcodeData.package;
        this.lastScanned.packageId = false;
        if (!recPackage && !packageType && !packageName) {
            return; // No Package data to process.
        }
        // Scan a new package and/or a package type -> Create a new package with those parameters.
        const currentLine = this.selectedLine || this.lastScannedLine;
        if (currentLine.package_id && packageType &&
            !recPackage && ! packageName &&
            currentLine.package_id.id !== packageType) {
            // Changes the package type for the scanned one.
            await this.orm.write('stock.quant.package', [currentLine.package_id.id], {
                package_type_id: packageType.id,
            });
            const message = _t(
                "Package type %s was correctly applied to the package %s",
                packageType.name,
                currentLine.package_id.name
            );
            barcodeData.stopped = true;
            return this.notification(message, { type: "success" });
        }
        if (!recPackage) {
            if (currentLine && !currentLine.package_id) {
                const valueList = {};
                if (packageName) {
                    valueList.name = packageName;
                }
                if (packageType) {
                    valueList.package_type_id = packageType.id;
                }
                const newPackageData = await this.orm.call(
                    'stock.quant.package',
                    'action_create_from_barcode',
                    [valueList]
                );
                this.cache.setCache(newPackageData);
                recPackage = newPackageData['stock.quant.package'][0];
            }
        }
        if (!recPackage && packageName) {
            const currentLine = this.selectedLine || this.lastScannedLine;
            if (currentLine && !currentLine.package_id) {
                const newPackageData = await this.orm.call(
                    'stock.quant.package',
                    'action_create_from_barcode',
                    [{ name: packageName }]
                );
                this.cache.setCache(newPackageData);
                recPackage = newPackageData['stock.quant.package'][0];
            }
        }
        if (!recPackage || (
            recPackage.location_id && recPackage.location_id != this.location.id
        )) {
            return;
        }
        // TODO: can check if quants already in cache to avoid to make a RPC if
        // there is all in it (or make the RPC only on missing quants).
        const res = await this.orm.call(
            'stock.quant',
            'get_stock_barcode_data_records',
            [recPackage.quant_ids]
        );
        const quants = res.records['stock.quant'];
        if (!quants.length) { // Empty package => Assigns it to the last scanned line.
            const currentLine = this.selectedLine || this.lastScannedLine;
            if (currentLine && !currentLine.package_id && !currentLine.result_package_id) {
                const fieldsParams = this._convertDataToFieldsParams({
                    resultPackage: recPackage,
                });
                await this.updateLine(currentLine, fieldsParams);
                barcodeData.stopped = true;
                this.selectedLineVirtualId = false;
                this.lastScanned.packageId = recPackage.id;
                this.trigger('update');
            }
            return;
        }
        this.cache.setCache(res.records);

        // Checks if the package is already scanned.
        let alreadyExisting = 0;
        for (const line of this.pageLines) {
            if (line.package_id && line.package_id.id === recPackage.id &&
                this.getQtyDone(line) > 0) {
                alreadyExisting++;
            }
        }
        if (alreadyExisting === quants.length) {
            barcodeData.error = _t("This package is already scanned.");
            return;
        }
        // For each quants, creates or increments a barcode line.
        for (const quant of quants) {
            const product = this.cache.getRecord('product.product', quant.product_id);
            const searchLineParams = Object.assign({}, barcodeData, { product });
            const currentLine = this._findLine(searchLineParams);
            if (currentLine) { // Updates an existing line.
                const fieldsParams = this._convertDataToFieldsParams({
                    quantity: quant.quantity,
                    lotName: barcodeData.lotName,
                    lot: barcodeData.lot,
                    package: recPackage,
                    owner: barcodeData.owner,
                });
                await this.updateLine(currentLine, fieldsParams);
            } else { // Creates a new line.
                const fieldsParams = this._convertDataToFieldsParams({
                    product,
                    quantity: quant.quantity,
                    lot: quant.lot_id,
                    package: quant.package_id,
                    resultPackage: quant.package_id,
                    owner: quant.owner_id,
                });
                const newLine = await this._createNewLine({ fieldsParams });
                newLine.inventory_quantity = quant.quantity;
            }
        }
        barcodeData.stopped = true;
        this.selectedLineVirtualId = false;
        this.lastScanned.packageId = recPackage.id;
        this.trigger('update');
    }

    _updateLineQty(line, args) {
        if (args.quantity) { // Set stock quantity.
            line.quantity = args.quantity;
        }
        if (args.inventory_quantity) { // Increments inventory quantity.
            if (args.uom) {
                // An UoM was passed alongside the quantity, needs to check it's
                // compatible with the product's UoM.
                const productUOM = this.cache.getRecord('uom.uom', line.product_id.uom_id);
                if (args.uom.category_id !== productUOM.category_id) {
                    // Not the same UoM's category -> Can't be converted.
                    const message = _t(
                        "Scanned quantity uses %s as Unit of Measure, but this UoM is not compatible with the product's one (%s).",
                        args.uom.name,
                        productUOM.name
                    );
                    return this.notification(message, { title: _t("Wrong Unit of Measure"), type: "warning" });
                } else if (args.uom.id !== productUOM.id) {
                    // Compatible but not the same UoM => Need a conversion.
                    args.inventory_quantity = (args.inventory_quantity / args.uom.factor) * productUOM.factor;
                }
            }
            line.inventory_quantity += args.inventory_quantity;
            line.inventory_quantity_set = true;
            if (line.product_id.tracking === 'serial' && (line.lot_name || line.lot_id)) {
                line.inventory_quantity = Math.max(0, Math.min(1, line.inventory_quantity));
            }
        }
    }

    async _updateLotName(line, lotName) {
        if (line.lot_name === lotName) {
            // No need to update the line's tracking number if it's already set.
            return Promise.resolve();
        }
        line.lot_name = lotName;
        // Checks if a quant exists for this line and updates the line in this case.
        const domain = [
            ['location_id', '=', line.location_id.id],
            ['product_id', '=', line.product_id.id],
            ['lot_id.name', '=', lotName],
            ['owner_id', '=', line.owner_id && line.owner_id.id],
            ['package_id', '=', line.package_id && line.package_id.id],
        ];
        const existingQuant = await this.orm.searchRead(
            'stock.quant',
            domain,
            ['id', 'quantity'],
            { limit: 1, load: false }
        );
        if (existingQuant.length) {
            Object.assign(line, existingQuant[0]);
            if (line.lot_id) {
                line.lot_id = await this.cache.getRecordByBarcode(lotName, 'stock.lot');
            }
        }
    }

    _canOverrideTrackingNumber(line, newLotName) {
        return super._canOverrideTrackingNumber(...arguments) && (!line.id || line.lot_id);
    }

    _createLinesState() {
        const today = new Date().toISOString().slice(0, 10);
        const lines = [];
        for (const id of Object.keys(this.cache.dbIdCache['stock.quant']).map(id => Number(id))) {
            const quant = this.cache.getRecord('stock.quant', id);
            if (quant.user_id !== this.userId || quant.inventory_date > today) {
                // Doesn't take quants who must be counted by another user or in the future.
                continue;
            }
            // Checks if this line is already in the quant state to get back
            // its `virtual_id` (and so, avoid to set a new `virtual_id`).
            const prevLine = this.currentState && this.currentState.lines.find(l => l.id === id);
            const previousVirtualId = prevLine && prevLine.virtual_id;
            quant.dummy_id = quant.dummy_id && Number(quant.dummy_id);
            quant.virtual_id = quant.dummy_id || previousVirtualId || this._uniqueVirtualId;
            quant.product_id = this.cache.getRecord('product.product', quant.product_id);
            quant.location_id = this.cache.getRecord('stock.location', quant.location_id);
            quant.lot_id = quant.lot_id && this.cache.getRecord('stock.lot', quant.lot_id);
            quant.package_id = quant.package_id && this.cache.getRecord('stock.quant.package', quant.package_id);
            quant.owner_id = quant.owner_id && this.cache.getRecord('res.partner', quant.owner_id);
            lines.push(Object.assign({}, quant));
        }
        return lines;
    }

    _getName() {
        return _t("Inventory Adjustment");
    }

    _getPrintOptions() {
        const options = super._getPrintOptions();
        const quantsToPrint = this.pageLines.filter(quant => quant.inventory_quantity_set);
        if (quantsToPrint.length === 0) {
            return { warning: _t("There is nothing to print in this page.") };
        }
        options.additionalContext = { active_ids: quantsToPrint.map(quant => quant.id) };
        return options;
    }

    _selectLine(line) {
        if (this.selectedLineVirtualId !== line.virtual_id) {
            // Unfolds the group where the line is, folds other lines' group.
            this.unfoldLineKey = this.groupKey(line);
        }
        super._selectLine(...arguments);
    }
}
