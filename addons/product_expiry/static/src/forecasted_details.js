import { patch } from "@web/core/utils/patch";
import { ForecastedDetails } from "@stock/stock_forecasted/forecasted_details";

patch(ForecastedDetails.prototype, {
    _freeStockCondition(line){
        return super._freeStockCondition(line) && line?.removal_date != -1;
    },
    _prepareLines() {
        if (this.props.docs.use_expiration_date) {
            this.props.docs.lines.sort((a, b) => (a.removal_date || 0) - (b.removal_date || 0));
        }
        super._prepareLines();
    },
    _prepareData(){
        // Whenever there's a Free Stock line without an expiration date,
        // remove the quantities "to remove" from this line to improve readibility
        super._prepareData();
        for (const productId of this.productIds){
            if (!(productId in this.FreeStockLinesPerProduct)){
                continue;
            }
            const lines = this.FreeStockLinesPerProduct[productId]
            let noRemovalDateLine = lines.find(line => !line.removal_date);
            let withRemovalDateLines = lines.filter(line => line.removal_date);
            if (noRemovalDateLine && withRemovalDateLines.length) {
                const sumQty = withRemovalDateLines.reduce((sum, line) => sum + (line.quantity || 0), 0);
                noRemovalDateLine.quantity = noRemovalDateLine.quantity - sumQty;
            }
            if (noRemovalDateLine && noRemovalDateLine?.quantity === 0 && withRemovalDateLines?.length){
                const removeIndex = this.lines.indexOf(noRemovalDateLine);
                this.lines.splice(removeIndex,1);
            }
        }
    },
    _sameLineRule(line, nextLine){
        const res = super._sameLineRule(line, nextLine);
        const FreeStock = this.FreeStockLinesPerProduct[line.product.id] || [];
        return res || (FreeStock.includes(line) && FreeStock.includes(nextLine));
    }
});
