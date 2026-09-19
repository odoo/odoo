export function getTaxDetailsOfLines(lines) {
    const taxDetails = {};
    for (const line of lines) {
        for (const taxData of line.get_all_prices().taxesData) {
            const taxId = taxData.tax.id;
            if (!taxDetails[taxId]) {
                taxDetails[taxId] = Object.assign({}, taxData, {
                    amount: 0.0,
                    base: 0.0,
                    tax_percentage: taxData.tax.amount,
                });
            }
            taxDetails[taxId].base += taxData.base_amount_currency;
            taxDetails[taxId].amount += taxData.tax_amount_currency;
        }
    }
    return Object.values(taxDetails);
}
