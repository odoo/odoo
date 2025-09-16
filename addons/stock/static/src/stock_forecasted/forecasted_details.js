import { formatFloat } from "@web/views/fields/formatters";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class ForecastedDetails extends Component {
    static template = "stock.ForecastedDetails";
    static props = { docs: Object, openView: Function, reloadReport: Function };

    setup() {
        this.orm = useService("orm");

        this.onHandCondition =
            this.props.docs.lines.length &&
            !this.props.docs.lines.some((line) => line.document_in || line.replenishment_filled);

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

<<<<<<< 73df73d663c5408142af695cf165102fdb45e2b4
||||||| 8024d8ad464592a2da6828e1c3525c8d34a27529
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
        let lastIndex;
        for(let i = 0; i < lines.length-1; i++){
            const line = lines[i];
            const nextLine = lines[i + 1];
            if (line.product.id != nextLine.product.id || !this._sameLineRule(line, nextLine)) {
                lastIndex = i+1;
                this.mergesLinesData[lastIndex] = {
                    rowcount: 1,
                    tot_qty: nextLine.quantity,
                };
                continue;
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

=======
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

>>>>>>> 60cbbb5792b181b32c693feac688fe2cbf4871c0
    displayReserve(line){
        return this.props.docs.user_can_edit_pickings && !line.in_transit && this.canReserveOperation(line);
    }

    canReserveOperation(line){
        return line.move_out?.picking_id;
    }

    get futureVirtualAvailable() {
        return this.props.docs.virtual_available + this.props.docs.qty.in - this.props.docs.qty.out;
    }

    get freeStockLabel() {
        return _t('Free Stock');
    }

    classForLine(line) {
        const greyBackground = !line.document_in && !line.reservation &&
            (!line.in_transit && line.replenishment_filled && !line.document_out && !line.removal_date)
            ||
            (line.in_transit && !line.move_out);
        return greyBackground ? 'bg-200' : '';
    }

    should_have_grey_bg(line){

    }
}
