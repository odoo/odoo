import { formatFloat } from "@web/views/fields/formatters";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class ForecastedDetails extends Component {
    static template = "stock.ForecastedDetails";
    static props = { docs: Object, openView: Function, reloadReport: Function };

    setup() {
        this.orm = useService("orm");
        this._groupLines();
        this._prepareLines();
        this._prepareData();
        this._mergeLines();

        this._formatFloat = (num) => {
            return formatFloat(num, { digits: this.props.docs.precision });
        };
    }

    async _reserve(move_id){
        await this.orm.call(
            'stock.forecasted_product_product',
            'action_reserve_linked_picks',
            [move_id],
        );
        this.props.reloadReport();
    }

    async _unreserve(move_id){
        await this.orm.call(
            'stock.forecasted_product_product',
            'action_unreserve_linked_picks',
            [move_id],
        );
        this.props.reloadReport();
    }

    async _onClickChangePriority(modelName, record) {
        const value = record.priority == "0" ? "1" : "0";

        await this.orm.call(modelName, "write", [[record.id], { priority: value }]);
        this.props.reloadReport();
    }

    _onHandCondition(line){
        return !line.document_in && !line.in_transit && line.replenishment_filled && line.document_out;
    }

    _reconciledCondition(line){
        return line.document_in && !line.in_transit && line.replenishment_filled && line.document_out;
    }

    _freeStockCondition(line){
        return !line.document_in && !line.in_transit && line.replenishment_filled && !line.document_out;
    }

    _notAvailableCondition(line){
        return !line.document_in && !line.in_transit && !line.replenishment_filled && line.document_out;
    }

    //Extend this to add new lines grouping
    _groupLines(){
        this._groupLinesByProduct();
        this._groupOnHandLinesByProduct();
        this._groupReconciledLinesByProduct();
        this._groupFreeStockLinesByProduct();
        this._groupNotAvailableLinesByProduct();
    }

    _groupLinesByProduct() {
        this.LinesPerProduct = {};
        for (const line of this.props.docs.lines) {
            const key = line.product.id;
            (this.LinesPerProduct[key] ??= []).push(line);
        }
    }

    _groupOnHandLinesByProduct() {
        this.OnHandLinesPerProduct = {};
        for (const line of this.props.docs.lines) {
            if (this._onHandCondition(line)) {
                const key = line.product.id;
                (this.OnHandLinesPerProduct[key] ??= []).push(line);
            }
        }
    }

    _groupReconciledLinesByProduct() {
        this.ReconciledLinesPerProduct = {};
        for (const line of this.props.docs.lines) {
            if (this._onHandCondition(line)) {
                const key = line.product.id;
                (this.ReconciledLinesPerProduct[key] ??= []).push(line);
            }
        }
    }

    _groupNotAvailableLinesByProduct() {
        this.NotAvailableLinesPerProduct = {};
        for (const line of this.props.docs.lines) {
            if (this._notAvailableCondition(line)) {
                const key = line.product.id;
                (this.NotAvailableLinesPerProduct[key] ??= []).push(line);
            }
        }
    }

    _groupFreeStockLinesByProduct() {
        this.FreeStockLinesPerProduct = {};
        for (const line of this.props.docs.lines) {
            if (this._freeStockCondition(line) && line?.removal_date !== -1) {
                const key = line.product.id;
                (this.FreeStockLinesPerProduct[key] ??= []).push(line);
            }
        }
    }

    _prepareLines(){
        if (this.multipleProducts) {
            this.props.docs.lines.sort((a, b) => (a.product.id || 0) - (b.product.id || 0));
        }
    }

    _prepareData(){
        this.OnHandTotalQty = Object.fromEntries(
            Object.entries(this.OnHandLinesPerProduct).map(([id, lines]) => [
                id,
                lines.reduce((sum, line) => sum + line.quantity, 0),
            ])
        );
        this.AvailableOnHandTotalQty = Object.fromEntries(
            Object.entries(this.OnHandLinesPerProduct).map(([id, lines]) => [
                id,
                lines.reduce((sum, line) => sum + (line.reservation ? 0 : line.quantity), 0),
            ])
        );
        for (const productId of this.productIds){
            if (!(productId in this.FreeStockLinesPerProduct) || !(productId in this.LinesPerProduct)){
                continue;
            }
            const lines = this.FreeStockLinesPerProduct[productId]
            if (this.LinesPerProduct[productId].length > 1 && lines.length == 1 && lines[0]?.quantity === 0 ){
                const removeIndex = this.lines.indexOf(lines[0]);
                this.lines.splice(removeIndex,1);
            }
        }
    }

    _mergeLines(){
        let lines = this.lines;
        this.mergesLinesData = {};
        let lastIndex = 0;
        for(let i = 0; i < lines.length-1; i++){
            const line = lines[i];
            const nextLine = lines[i + 1];
            if (line.product.id != nextLine.product.id || !this._sameLineRule(line, nextLine)) {
                lastIndex = i+1;
                continue;
            }
            if (!this.mergesLinesData[lastIndex]){
                this.mergesLinesData[lastIndex] = {
                    rowcount: 1,
                    tot_qty: line.quantity,
                };
            }
            this.mergesLinesData[lastIndex].rowcount += 1;
            this.mergesLinesData[lastIndex].tot_qty += nextLine.quantity;
        }
    }

    _sameLineRule(line, nextLine){
        const OnHand = this.OnHandLinesPerProduct[line.product.id] || [];
        const NotAvailable = this.NotAvailableLinesPerProduct[line.product.id] || [];
        return  this.sameDocumentIn(line, nextLine) || (OnHand.includes(line) && OnHand.includes(nextLine)) || (NotAvailable.includes(line) && NotAvailable.includes(nextLine));
    }

    displayReserve(line){
        let splittedLine = true;
        if(this.line_index - 1 >= 0){
            const previousLine = this.lines[this.line_index - 1];
            const sameProduct = this.line.product.id == previousLine.product.id;
            const isOnHandSplittedLine = this.OnHandLinesPerProduct[line.product.id] && this.OnHandLinesPerProduct[line.product.id].some(l => this.sameDocumentOut(l, line))
            const isReconciledSplittedLine = this.ReconciledLinesPerProduct[line.product.id] && !this.isReconciled(line) && this.ReconciledLinesPerProduct[line.product.id].some(l => this.sameDocumentOut(l, line))
            splittedLine = sameProduct && (this.sameDocumentOut(line, previousLine) || isOnHandSplittedLine || isReconciledSplittedLine);
        }
        const hasFreeStock = this.props.docs.product[line.product.id].free_qty > 0;
        return this.props.docs.user_can_edit_pickings && !line.in_transit && this.canReserveOperation(line) &&
            (this.isOnHand(line) || (hasFreeStock && !splittedLine));
    }

    canReserveOperation(line){
        return line.move_out?.picking_id;
    }

    futureVirtualAvailable(line) {
        const product = this.props.docs.product[line.product.id]
        return product.virtual_available + product.qty.in - product.qty.out;
    }

    sameDocumentIn(line1, line2){
        return this._sameDocument(line1, line2, 'document_in');
    }

    sameDocumentOut(line1, line2){
        return this._sameDocument(line1, line2, 'document_out');
    }

    _sameDocument(line1, line2, docField) {
        return (
            line1[docField] && line2[docField] &&
            line1[docField].id === line2[docField].id &&
            line1[docField]._name === line2[docField]._name &&
            line1[docField].name === line2[docField].name
        );
    }

    isOnHand(line){
        return this.OnHandLinesPerProduct[line.product.id] && this.OnHandLinesPerProduct[line.product.id].includes(this.lines[this.line_index]);
    }

    isReconciled(line){
        return this.ReconciledLinesPerProduct[line.product.id] && this.ReconciledLinesPerProduct[line.product.id].includes(this.lines[this.line_index]);
    }

    get freeStockLabel() {
        return _t('Free Stock');
    }

    get lines() {
        return this.props.docs.lines;
    }

    get multipleProducts() {
        return this.props.docs.multiple_product;
    }

    get productIds(){
        return Object.keys(this.props.docs.product).map(Number);
    }
}
