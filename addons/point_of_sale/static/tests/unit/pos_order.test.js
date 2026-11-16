import { expect, test } from "@odoo/hoot";
import { getTaxDetailsOfLines } from "@point_of_sale/app/models/utils/tax_details";

test("get_tax_details_of_lines groups tax details by tax id", () => {
    const taxGroup = { id: 1, name: "Sales Tax" };
    const taxes = [
        { id: 3, name: "6%", amount: 6, tax_group_id: taxGroup },
        { id: 4, name: "7%", amount: 7, tax_group_id: taxGroup },
        { id: 5, name: "9%", amount: 9, tax_group_id: taxGroup },
    ];
    const lines = [
        makeLineTaxData(taxes[0], 12, 0.72),
        makeLineTaxData(taxes[1], 1.25, 0.09),
        makeLineTaxData(taxes[2], 1.8, 0.16),
    ];

    const taxDetails = getTaxDetailsOfLines(lines);

    expect(taxDetails).toHaveLength(3);
    expect(taxDetails.map((detail) => detail.tax.id)).toEqual([3, 4, 5]);
    expect(taxDetails.map((detail) => detail.tax_percentage)).toEqual([6, 7, 9]);
    expect(taxDetails.map((detail) => detail.base)).toEqual([12, 1.25, 1.8]);
    expect(taxDetails.map((detail) => detail.amount)).toEqual([0.72, 0.09, 0.16]);
});

function makeLineTaxData(tax, baseAmount, taxAmount) {
    return {
        get_all_prices() {
            return {
                taxesData: [
                    {
                        tax,
                        base_amount_currency: baseAmount,
                        tax_amount_currency: taxAmount,
                    },
                ],
            };
        },
    };
}
