/** @odoo-module **/

import BarcodePickingModel from '@stock_barcode/models/barcode_picking_model';
import { _t } from "@web/core/l10n/translation";

export default class BarcodeMRPModel extends BarcodePickingModel {
    constructor(params) {
        super(...arguments);
        this.lineModel = 'stock.move.line';
        this.showBackOrderDialog = false;
        this.validateMessage = _t("The manufacturing order has been validated");
        this.validateMethod = 'button_mark_done';
        this.validateContext = {};
        this.backorderModel = 'mrp.production';
        this.actionName = 'stock_barcode_mrp.stock_barcode_mo_client_action';
        this.componentLoaded = false;
        this.displayByProduct = false;
    }

    get cancelLabel() {
        return _t("Cancel Manufacturing Order");
    }

    get canScrap() {
        const { state } = this.record;
        return state != 'cancel' && state != 'draft';
    }

    _cancelNotification() {
        this.notification(_t("The Manufacturing Order has been cancelled"));
    }

    get printButtons() {
        const buttons = [
            {
                name: _t("Print Production Order"),
                class: 'o_print_production',
                action: 'mrp.action_report_production_order'
            },
            {
                name: _t("Print Finished Product Label (ZPL)"),
                class: 'o_print_finished_product_zpl',
                action: 'mrp.label_manufacture_template',
            },
            {
                name: _t("Print Finished Product Label (PDF)"),
                class: 'o_print_finsihed_product_pdf',
                action: 'mrp.action_report_finished_product',
            },
        ];
        return buttons;
    }

    get barcodeInfo() {
        const barcodeInfo = super.barcodeInfo;
        if (this.isCancelled || this.isDone) {
            return {
                class: this.isDone ? 'order_already_done' : 'order_already_cancelled',
                message: this.isDone ?
                    _t("This order is already done") :
                    _t("This order is cancelled"),
                icon: "exclamation-triangle",
                warning: true,
            };
        }
        if (barcodeInfo.class === 'scan_product' && this.record.product_id) {
            return {
                message: _t("Scan a component"),
                class: "scan_component",
                icon: "tags",
            };
        }
        else if (barcodeInfo.class === 'scan_validate' && this.record.qty_producing < this.record.product_qty) {
            return {
                message: _t("Scan your final product or more components"),
                class: "scan_final_product",
                icon: "tags",
            };
        }
        else if (barcodeInfo.class === 'scan_validate') {
            barcodeInfo.message = 'Press Produce All or scan another component';
        }
        return barcodeInfo;
    }

    get displayValidateButton() {
        return true;
    }

    get displayPutInPackButton() {
        return false;
    }

    get moveIds() {
        return this.record.move_raw_ids;
    }

    get useExistingLots() {
        return true;
    }

    get isComplete() {
        return this.record.qty_producing >= this.record.product_qty;
    }

    get highlightValidateButton() {
        return this.canBeValidate && this.isComplete;
    }

    get pageLines() {
        if (this.displayByProduct) {
            return this.currentState.lines.filter( line => line.byProduct);
        }
        return this.currentState.lines.filter( line => !line.byProduct);
    }

    get displaySourceLocation() {
        return this.groups.group_stock_multi_locations;
    }

    get canBeValidate() {
        return ['confirmed', 'progress', 'to_close'].includes(this.record.state);
    }

    get canCreateNewLot() {
        return true;
    }

    get selectedLine() {
        if (this.record.virtualId === this.selectedLineVirtualId) {
            return this._getFinalProductLine();
        }
        return super.selectedLine;
    }

    get backordersDomain() {
        return [
            ['id', 'not in', this.record.backorder_ids],
            ['procurement_group_id', '=', this.record.procurement_group_id],
            ['state', '=', 'confirmed'],
        ];
    }

    /** Fetch data and set state */

    getActionRefresh(newId) {
        return {
            route: '/stock_barcode/get_barcode_data',
            params: {model: this.resModel, res_id: newId || this.resId},
        };
    }

    setData(data) {
        data.actionId = this.actionId || data.actionId;
        super.setData(...arguments);
        this.headerViewId = data.data.header_view_id;
        this.scrapViewId = data.data.scrap_view_id;
    }

    _getName() {
        if (!this.resId) {
            return _t('New');
        }
        return super._getName(...arguments);
    }

    async refreshCache(records) {
        if (!this.resId && "mrp.production" in records) {
            /** A new MO has no ID because it requires the finish product to be saved.
             * If there is no `resId` but a production belongs to the records, we assume this record
             * is the current MO who as been saved.
             */
            this.resId = records["mrp.production"]?.[0]?.id;
        }
        return super.refreshCache(...arguments);
    }


    _createState() {
        super._createState(...arguments);
        this.initialState.record = JSON.parse(JSON.stringify(this.record));
        this.trigger('update');
    }

    _getModelRecord() {
        const record = this.resId && this.cache.getRecord(this.resModel, this.resId);
        if (!record) {
            return {};
        }
        record.product_id = this.cache.getRecord('product.product', record.product_id);
        record.product_uom_id = this.cache.getRecord('uom.uom', record.product_uom_id);
        if (record.lot_producing_id) {
            record.lot_producing_id = this.cache.getRecord('stock.lot', record.lot_producing_id);
        }
        if (record.picking_type_id && record.state !== "cancel") {
            record.picking_type_id = this.cache.getRecord('stock.picking.type', record.picking_type_id);
        }
        return record;
    }

    _getMoveLineData(id){
        const smlData = super._getMoveLineData(id);
        smlData.move_id = smlData.move_id && this.cache.getRecord('stock.move', smlData.move_id);
        return smlData;
    }

    _createLinesState() {
        const lines = [];
        if (!this.resId && !this.record.id) {
            return [];
        }
        const mo = this.cache.getRecord(this.resModel, this.resId || this.record.id);
        for (const id of mo.move_raw_line_ids) {
            lines.push(this._getMoveLineData(id));
        }
        for (const id of mo.move_byproduct_line_ids) {
            const line = this._getMoveLineData(id);
            line.byProduct = true;
            lines.push(line);
        }
        this.componentLoaded = true;
        return lines;
    }

    get reloadingMoveLines() {
        return super.reloadingMoveLines && this.componentLoaded;
    }

    async confirmAndSetData(recordId) {
        this.resId = recordId;
        await this.orm.call('mrp.production', 'action_confirm', [[this.resId]]);
        const { route, params } = this.getActionRefresh(recordId);
        const result = await this.rpc(route, params);
        this.setData(result);
    }

    /** Line Operations */

    _checkBarcode(barcodeData) {
        if (this.displayByProduct && barcodeData?.product?.id == this.record.product_id.id){
            return {
                title: _t("Product not Allowed"),
                message: _t("You can't add the final product of a MO as a byproduct."),
                error: true,
            };
        }
        return super._checkBarcode(...arguments);
    }

    _getFinalProductLine() {
        if (!this.record.virtualId) {
            this.record.virtualId = this._uniqueVirtualId;
        }
        if (this.record.location_dest_id && this.record.location_src_id) {
            return {
                virtual_id: this.record.virtualId,
                product_id: this.record.product_id,
                product_uom_id: this.record.product_uom_id,
                location_id: this.cache.getRecord('stock.location', this.record.location_src_id),
                location_dest_id: this.cache.getRecord('stock.location', this.record.location_dest_id),
                lot_id: this.record.lot_producing_id,
                lot_name: this.record.lot_name,
                finalProduct: true,
                package_id: false,
                qty_done: this.record.qty_producing,
                reserved_uom_qty: this.record.product_qty,
            }
        }
    }

    _findLine(barcodeData) {
        const { product } = barcodeData;
        if (this.record.product_id && product.id == this.record.product_id.id) {
            return this._getFinalProductLine();
        }
        return super._findLine(...arguments);
    }

    _getNewLineDefaultValues(fieldsParams) {
        const defaultValues = super._getNewLineDefaultValues(...arguments);
        delete defaultValues.picking_id;
        defaultValues.production_id = this.resId;
        if (this.displayByProduct) {
            defaultValues.byProduct = true;
        }
        return defaultValues
    }

    _shouldSearchForAnotherLot(barcodeData, filters) {
        return !barcodeData.match && filters['stock.lot'];
    }

    _shouldCreateLineOnExceed(line) {
        if (line.finalProduct) {
            return false;
        }
        return super._shouldCreateLineOnExceed(line);
    }

    async createNewLine(params) {
        const { product_id } = params.fieldsParams;
        if (!this.record.product_id && product_id ) {
            this.record.product_id = product_id;
            return await this.save();
        }
        return super.createNewLine(...arguments);
    }

    updateLine(line, args) {
        // handle header line updates here
        if (line.finalProduct) {
            if (args.lot_name) {
                this.record.lot_name = args.lot_name;
            }
            if (args.lot_id) {
                this.record.lot_producing_id = args.lot_id;
            }
            this.produceQty();
            return;
        }
        let move = args.move_id;
        if (move) {
            if (typeof move === 'number') {
                move = this.cache.getRecord('stock.move', move);
            }
            line.move_id = move;
        }
        args.manual_consumption = 'manual_consumption' in args ? args.manual_consumption : true;
        super.updateLine(...arguments);
        if (args.move_uom_id) {
            line.product_uom_id = this.cache.getRecord('uom.uom', args.move_uom_id);
        }
    }

    updateLineQty(virtualId, qty=1, manual_consumption=true, location_id=null) {
        this.actionMutex.exec(() => {
            const line = this.currentState.lines.find(l => l.virtual_id === virtualId);
            this.updateLine(line, {manual_consumption, location_id, qty_done: qty});
            this.trigger('update');
        });
    }

    _updateLineQty(line, args) {
        line.manual_consumption = args.manual_consumption;
        super._updateLineQty(...arguments);
    }

    lineIsFaulty(line) {
        return line.reserved_uom_qty && line.qty_done > line.reserved_uom_qty;
    }

    _incrementTrackedLine() {
        return false;
    }

    _defaultLocation(params = {}) {
        const locId = params.newByProduct ? this.record.production_location_id : this.record.location_src_id
        return this.cache.getRecord('stock.location', locId);
    }

    _defaultDestLocation(params = {}) {
        const locId = params.newByProduct ? this.record.location_dest_id : this.record.production_location_id
        return this.cache.getRecord('stock.location', locId);
    }

    _getNewLineDefaultContext(params = {}) {
        return {
            default_company_id: this.record.company_id,
            default_location_id: this._defaultLocation(params).id,
            default_location_dest_id: params.scrapProduct? null : this._defaultDestLocation(params).id,
            default_product_uom_id: this.record.product_uom_id.id,
            default_production_id: this.resId,
            default_qty_done: 0,
            final_product_id: this.record.product_id.id,
            newByProduct: params.newByProduct,
        };
    }

    autoConsumeLine(line) {
        return line.reserved_uom_qty && (line.product_id.tracking == 'none' || this.config.use_auto_consume_components_lots);
    }

    isManualConsumptionLine(line) {
        const parentLine = this._getParentLine(line);
        if (!parentLine) {
            return line.manual_consumption || !line.reserved_uom_qty;
        }
        for (const subLine of parentLine.lines) {
            if (subLine.manual_consumption || ! subLine.reserved_uom_qty) {
                return true;
            }
        }
        return false;
    }

    produceQty(quantity = 1) {
        const new_producing = this.record.qty_producing + quantity;
        if (this.record.product_id.tracking == 'serial' && new_producing > 1) {
            const message = _t(`To produce more products create a new MO.`);
            this.notification(message, { type: 'danger' });
            return;
        }
        this.record.qty_producing = new_producing;
        const ratio = quantity / this.record.product_qty;

        for (const moveId of [...this.record.move_raw_ids, ...this.record.move_byproduct_ids]) {
            const move = this.cache.getRecord('stock.move', moveId);
            let manualMove = false;
            const moveLines = this.currentState.lines.filter(line => line.move_id?.id === moveId);
            let qtyRemaining = ratio * move.product_uom_qty;
            for (const line of moveLines) {
                if (this.isManualConsumptionLine(line) || qtyRemaining === 0) {
                    manualMove = true;
                    break;
                }
                if (!this.autoConsumeLine(line)) {
                    continue;
                }
                const qtyToAdd = Math.min(qtyRemaining, line.reserved_uom_qty);
                this.updateLineQty(line.virtual_id, qtyToAdd, false, line.location_id);
                qtyRemaining -= qtyToAdd;
            }
            if (qtyRemaining > 0 && !manualMove) {
                const fieldsParams = {
                    product_id: this.cache.getRecord('product.product', move.product_id),
                    location_id: move.location_id,
                    qty_done: qtyRemaining,
                    move_id: moveId,
                }
                if (this.groups.group_uom) {
                    fieldsParams.move_uom_id = move.product_uom;
                }
                this._createNewLine({ fieldsParams });
            }
        }
        this.trigger('update');
    }

    async generateSerial() {
        await this.save();
        const res = await this.orm.call('mrp.production', 'set_lot_producing', [[this.resId]]);
        this.record.lot_producing_id = res[0][0];
        const action = res[1]
        if(this.record.product_id.tracking == 'serial' && this.record.qty_producing === 0) {
            this.produceQty();
            if (action) {
                return this.action.doAction(action);
            }
            return;
        }
        if (action) {
            return this.action.doAction(action);
        }
        this.trigger('update');
    }

    askBeforeNewLinesCreation(product) {
        return false;
    }

    /** Save commands */

    _getPrintOptions() {
        if(!this.resId) {
            return {};
        }
        return {
            additionalContext: {
                active_ids: [this.resId],
            }
        }
    }

    _getFieldToWrite() {
        const fields = super._getFieldToWrite(...arguments);
        fields.push('manual_consumption');
        return fields
    }

    _getSaveCommand() {
        // only need the last two arguments (id / 0 and vals) from each command
        const commands = this._getSaveLineCommand().map(cmd => [this.lineModel, cmd[1], cmd[2]]);
        // we need a product before we can create an MO
        if (this.record.product_id) {
            const vals = this._getRecordSaveVals();
            if (Object.keys(vals).length) {
                commands.push([this.resModel, this.resId || 0,  vals]);
            }
        }
        if (commands.length) {
            return {
                route: '/stock_barcode_mrp/save_barcode_data',
                params: {
                    model_vals: commands,
                },
            };
        }
        return {};
    }

    _getRecordFieldsToWrite() {
        return [
            'qty_producing',
            'product_qty',
            'lot_producing_id',
            'product_id',
        ]
    }

    _getRecordSaveVals() {
        // compare current record with initial value;
        const res = {};
        const writeFields = this._getRecordFieldsToWrite();
        for (let fieldName of writeFields) {
            let value = this.record[fieldName];
            value = typeof value === 'object' ? value.id: value;
            let initialValue = this.initialState.record[fieldName];
            initialValue = typeof initialValue === 'object' ? initialValue.id: initialValue;
            if (value !== initialValue) {
                res[fieldName] = value;
            }
        }

        if (!this.record.lot_producing_id && this.record.lot_name) {
            res.lot_producing_id = {
                name: this.record.lot_name,
                product_id: this.record.product_id.id,
                company_id: this.record.company_id, // only the id is fetched from the backend
            }
        }
        return res
    }

    _createCommandVals(line) {
        const values = super._createCommandVals(...arguments);
        values.production_id = this.resId;
        values.company_id = this.record.company_id;
        if (line.byProduct){
            values.byProduct = true;
        }
        return values;
    }

    _getCommands() {
        return Object.assign(super._getCommands(), {
            'O-BTN.print-mo': this.print.bind(this, 'mrp.action_report_production_order'),
            'O-BTN.print-product-label': this.print.bind(this, 'mrp.action_report_finished_product'),
        });
    }

}
