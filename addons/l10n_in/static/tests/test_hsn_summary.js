/** @odoo-module **/

import {
    fixed_tax,
    group_of_taxes,
    percent_tax,
} from "@account/../tests/test_account_tax";
import { l10n_in_get_hsn_summary_table } from "@l10n_in/helpers/hsn_summary";

const test_hsn_code_1 = "1234"
const test_hsn_code_2 = "4321"

const uom_unit = "unit";
const uom_dozen = "dozen";

const igst_0 = percent_tax(0.0, {_l10n_in_tax_type: "igst"});
const igst_5 = percent_tax(5.0, {_l10n_in_tax_type: "igst"});
const igst_18 = percent_tax(18.0, {_l10n_in_tax_type: "igst"});
const sgst_2_5 = percent_tax(2.5, {_l10n_in_tax_type: "sgst"});
const cgst_2_5 = percent_tax(2.5, {_l10n_in_tax_type: "cgst"});
const gst_5 = group_of_taxes([sgst_2_5, cgst_2_5]);
const sgst_9 = percent_tax(9.0, {_l10n_in_tax_type: "sgst"});
const cgst_9 = percent_tax(9.0, {_l10n_in_tax_type: "cgst"});
const gst_18 = group_of_taxes([sgst_9, cgst_9]);
const cess_5 = percent_tax(5.0, {_l10n_in_tax_type: "cess"});
const cess_1591 = fixed_tax(1.591, {_l10n_in_tax_type: "cess"});
const cess_5_plus_1591 = group_of_taxes([cess_5, cess_1591]);
const exempt_0 = percent_tax(0.0);

export function create_base_line(l10n_in_hsn_code, quantity, price_unit, uom, taxes){
    return {
        l10n_in_hsn_code: l10n_in_hsn_code,
        quantity: quantity,
        price_unit: price_unit,
        uom: uom,
        taxes: taxes,
    }
}

export function assert_hsn_summary(assert, base_lines, display_uom, expected_values){
    const hsn_summary = l10n_in_get_hsn_summary_table(base_lines, display_uom);
    assert.deepEqual(
        {...hsn_summary, items: hsn_summary.items.length},
        {...expected_values, items: expected_values.items.length},
    );
    for (const [i, item] of hsn_summary.items.entries()) {
        assert.deepEqual(item, expected_values.items[i]);
    }
}

QUnit.module("test_l10n_in_hsn_summary", ({}) => {

    QUnit.test("test_l10n_in_hsn_summary_1", async (assert) => {
        assert.expect(17);
        const base_lines = [
            create_base_line(test_hsn_code_1, 2.0, 100.0, uom_unit, [gst_5]),
            create_base_line(test_hsn_code_1, 1.0, 600.0, uom_unit, [gst_5]),
            create_base_line(test_hsn_code_1, 5.0, 300.0, uom_unit, [gst_5]),
            create_base_line(test_hsn_code_1, 2.0, 100.0, uom_unit, [gst_18]),
            create_base_line(test_hsn_code_1, 1.0, 600.0, uom_unit, [gst_18]),
            create_base_line(test_hsn_code_1, 5.0, 300.0, uom_unit, [gst_18]),
        ];
        assert_hsn_summary(assert, base_lines, false, {
            has_igst: false,
            has_gst: true,
            has_cess: false,
            nb_columns: 7,
            display_uom: false,
            items: [
                {
                    l10n_in_hsn_code: test_hsn_code_1,
                    quantity: 8.0,
                    uom: uom_unit,
                    rate: 5.0,
                    amount_untaxed: 2300.0,
                    tax_amount_igst: 0.0,
                    tax_amount_cgst: 57.5,
                    tax_amount_sgst: 57.5,
                    tax_amount_cess: 0.0,
                },
                {
                    l10n_in_hsn_code: test_hsn_code_1,
                    quantity: 8.0,
                    uom: uom_unit,
                    rate: 18.0,
                    amount_untaxed: 2300.0,
                    tax_amount_igst: 0.0,
                    tax_amount_cgst: 207.0,
                    tax_amount_sgst: 207.0,
                    tax_amount_cess: 0.0,
                },
            ],
        });

        // Change the UOM of the second line.
        base_lines[1].uom = uom_dozen;
        base_lines[1].price_unit = 12000;

        assert_hsn_summary(assert, base_lines, false, {
            has_igst: false,
            has_gst: true,
            has_cess: false,
            nb_columns: 7,
            display_uom: false,
            items: [
                {
                    l10n_in_hsn_code: test_hsn_code_1,
                    quantity: 7.0,
                    uom: uom_unit,
                    rate: 5.0,
                    amount_untaxed: 1700.0,
                    tax_amount_igst: 0.0,
                    tax_amount_cgst: 42.5,
                    tax_amount_sgst: 42.5,
                    tax_amount_cess: 0.0,
                },
                {
                    l10n_in_hsn_code: test_hsn_code_1,
                    quantity: 1.0,
                    uom: uom_dozen,
                    rate: 5.0,
                    amount_untaxed: 12000.0,
                    tax_amount_igst: 0.0,
                    tax_amount_cgst: 300.0,
                    tax_amount_sgst: 300.0,
                    tax_amount_cess: 0.0,
                },
                {
                    l10n_in_hsn_code: test_hsn_code_1,
                    quantity: 8.0,
                    uom: uom_unit,
                    rate: 18.0,
                    amount_untaxed: 2300.0,
                    tax_amount_igst: 0.0,
                    tax_amount_cgst: 207.0,
                    tax_amount_sgst: 207.0,
                    tax_amount_cess: 0.0,
                },
            ],
        });

        // Change GST 5% taxes to IGST.
        base_lines[0].taxes = [igst_5];
        base_lines[1].taxes = [igst_5];
        base_lines[2].taxes = [igst_5];

        assert_hsn_summary(assert, base_lines, false, {
            has_igst: true,
            has_gst: true,
            has_cess: false,
            nb_columns: 8,
            display_uom: false,
            items: [
                {
                    l10n_in_hsn_code: test_hsn_code_1,
                    quantity: 7.0,
                    uom: uom_unit,
                    rate: 5.0,
                    amount_untaxed: 1700.0,
                    tax_amount_igst: 85.0,
                    tax_amount_cgst: 0.0,
                    tax_amount_sgst: 0.0,
                    tax_amount_cess: 0.0,
                },
                {
                    l10n_in_hsn_code: test_hsn_code_1,
                    quantity: 1.0,
                    uom: uom_dozen,
                    rate: 5.0,
                    amount_untaxed: 12000.0,
                    tax_amount_igst: 600.0,
                    tax_amount_cgst: 0.0,
                    tax_amount_sgst: 0.0,
                    tax_amount_cess: 0.0,
                },
                {
                    l10n_in_hsn_code: test_hsn_code_1,
                    quantity: 8.0,
                    uom: uom_unit,
                    rate: 18.0,
                    amount_untaxed: 2300.0,
                    tax_amount_igst: 0.0,
                    tax_amount_cgst: 207.0,
                    tax_amount_sgst: 207.0,
                    tax_amount_cess: 0.0,
                },
            ],
        });

        base_lines[1].uom = uom_unit;
        base_lines[1].price_unit = 600.0;
        base_lines[1].taxes = [igst_5];

        assert_hsn_summary(assert, base_lines, false, {
            has_igst: true,
            has_gst: true,
            has_cess: false,
            nb_columns: 8,
            display_uom: false,
            items: [
                {
                    l10n_in_hsn_code: test_hsn_code_1,
                    quantity: 8.0,
                    uom: uom_unit,
                    rate: 5.0,
                    amount_untaxed: 2300.0,
                    tax_amount_igst: 115.0,
                    tax_amount_cgst: 0.0,
                    tax_amount_sgst: 0.0,
                    tax_amount_cess: 0.0,
                },
                {
                    l10n_in_hsn_code: test_hsn_code_1,
                    quantity: 8.0,
                    uom: uom_unit,
                    rate: 18.0,
                    amount_untaxed: 2300.0,
                    tax_amount_igst: 0.0,
                    tax_amount_cgst: 207.0,
                    tax_amount_sgst: 207.0,
                    tax_amount_cess: 0.0,
                },
            ],
        });

        // Change GST 18% taxes to IGST.
        base_lines[3].taxes = [igst_18];
        base_lines[4].taxes = [igst_18];
        base_lines[5].taxes = [igst_18];

        assert_hsn_summary(assert, base_lines, false, {
            has_igst: true,
            has_gst: false,
            has_cess: false,
            nb_columns: 6,
            display_uom: false,
            items: [
                {
                    l10n_in_hsn_code: test_hsn_code_1,
                    quantity: 8.0,
                    uom: uom_unit,
                    rate: 5.0,
                    amount_untaxed: 2300.0,
                    tax_amount_igst: 115.0,
                    tax_amount_cgst: 0.0,
                    tax_amount_sgst: 0.0,
                    tax_amount_cess: 0.0,
                },
                {
                    l10n_in_hsn_code: test_hsn_code_1,
                    quantity: 8.0,
                    uom: uom_unit,
                    rate: 18.0,
                    amount_untaxed: 2300.0,
                    tax_amount_igst: 414.0,
                    tax_amount_cgst: 0.0,
                    tax_amount_sgst: 0.0,
                    tax_amount_cess: 0.0,
                },
            ],
        });
    });

    QUnit.test("test_l10n_in_hsn_summary_2", async (assert) => {
        assert.expect(4);
        const base_lines = [
            create_base_line(test_hsn_code_1, 1.0, 15.80, uom_unit, [gst_18, cess_5_plus_1591]),
        ];
        assert_hsn_summary(assert, base_lines, false, {
            has_igst: false,
            has_gst: true,
            has_cess: true,
            nb_columns: 8,
            display_uom: false,
            items: [
                {
                    l10n_in_hsn_code: test_hsn_code_1,
                    quantity: 1.0,
                    uom: uom_unit,
                    rate: 18.0,
                    amount_untaxed: 15.8,
                    tax_amount_igst: 0.0,
                    tax_amount_cgst: 1.42,
                    tax_amount_sgst: 1.42,
                    tax_amount_cess: 2.38,
                },
            ],
        });

        base_lines[0].taxes = [igst_18, cess_5_plus_1591];
        assert_hsn_summary(assert, base_lines, false, {
            has_igst: true,
            has_gst: false,
            has_cess: true,
            nb_columns: 7,
            display_uom: false,
            items: [
                {
                    l10n_in_hsn_code: test_hsn_code_1,
                    quantity: 1.0,
                    uom: uom_unit,
                    rate: 18.0,
                    amount_untaxed: 15.8,
                    tax_amount_igst: 2.84,
                    tax_amount_cgst: 0.0,
                    tax_amount_sgst: 0.0,
                    tax_amount_cess: 2.38,
                },
            ],
        });
    });

    QUnit.test("test_l10n_in_hsn_summary_3", async (assert) => {
        assert.expect(6);
        const base_lines = [
            create_base_line(test_hsn_code_1, 1.0, 100.0, uom_unit, [gst_18]),
            create_base_line(test_hsn_code_1, 2.0, 50.0, uom_unit, [gst_18]),
            create_base_line(test_hsn_code_2, 1.0, 100.0, uom_unit, [gst_18]),
            create_base_line(test_hsn_code_2, 2.0, 50.0, uom_unit, [gst_18]),
        ];
        assert_hsn_summary(assert, base_lines, false, {
            has_igst: false,
            has_gst: true,
            has_cess: false,
            nb_columns: 7,
            display_uom: false,
            items: [
                {
                    l10n_in_hsn_code: test_hsn_code_1,
                    quantity: 3.0,
                    uom: uom_unit,
                    rate: 18.0,
                    amount_untaxed: 200.0,
                    tax_amount_igst: 0.0,
                    tax_amount_cgst: 18.0,
                    tax_amount_sgst: 18.0,
                    tax_amount_cess: 0.0,
                },
                {
                    l10n_in_hsn_code: test_hsn_code_2,
                    quantity: 3.0,
                    uom: uom_unit,
                    rate: 18.0,
                    amount_untaxed: 200.0,
                    tax_amount_igst: 0.0,
                    tax_amount_cgst: 18.0,
                    tax_amount_sgst: 18.0,
                    tax_amount_cess: 0.0,
                },
            ],
        });

        // Change GST 18% taxes to IGST.
        base_lines[0].taxes = [igst_18];
        base_lines[1].taxes = [igst_18];
        base_lines[2].taxes = [igst_18];
        base_lines[3].taxes = [igst_18];

        assert_hsn_summary(assert, base_lines, false, {
            has_igst: true,
            has_gst: false,
            has_cess: false,
            nb_columns: 6,
            display_uom: false,
            items: [
                {
                    l10n_in_hsn_code: test_hsn_code_1,
                    quantity: 3.0,
                    uom: uom_unit,
                    rate: 18.0,
                    amount_untaxed: 200.0,
                    tax_amount_igst: 36.0,
                    tax_amount_cgst: 0.0,
                    tax_amount_sgst: 0.0,
                    tax_amount_cess: 0.0,
                },
                {
                    l10n_in_hsn_code: test_hsn_code_2,
                    quantity: 3.0,
                    uom: uom_unit,
                    rate: 18.0,
                    amount_untaxed: 200.0,
                    tax_amount_igst: 36.0,
                    tax_amount_cgst: 0.0,
                    tax_amount_sgst: 0.0,
                    tax_amount_cess: 0.0,
                },
            ],
        });
    });

    QUnit.test("test_l10n_in_hsn_summary_4", async (assert) => {
        assert.expect(7);
        const base_lines = [
            create_base_line(test_hsn_code_1, 1.0, 350.0, uom_unit, []),
            create_base_line(test_hsn_code_1, 1.0, 350.0, uom_unit, []),
        ];
        assert_hsn_summary(assert, base_lines, false, {
            has_igst: false,
            has_gst: false,
            has_cess: false,
            nb_columns: 5,
            display_uom: false,
            items: [
                {
                    l10n_in_hsn_code: test_hsn_code_1,
                    quantity: 2.0,
                    uom: uom_unit,
                    rate: 0.0,
                    amount_untaxed: 700.0,
                    tax_amount_igst: 0.0,
                    tax_amount_cgst: 0.0,
                    tax_amount_sgst: 0.0,
                    tax_amount_cess: 0.0,
                },
            ],
        });

        // No tax to IGST 0%/exempt.
        base_lines[0].taxes = [igst_0];
        base_lines[1].taxes = [exempt_0];

        assert_hsn_summary(assert, base_lines, false, {
            has_igst: true,
            has_gst: false,
            has_cess: false,
            nb_columns: 6,
            display_uom: false,
            items: [
                {
                    l10n_in_hsn_code: test_hsn_code_1,
                    quantity: 2.0,
                    uom: uom_unit,
                    rate: 0.0,
                    amount_untaxed: 700.0,
                    tax_amount_igst: 0.0,
                    tax_amount_cgst: 0.0,
                    tax_amount_sgst: 0.0,
                    tax_amount_cess: 0.0,
                },
            ],
        });

        // Put one IGST 18% to get a value on the IGST column.
        base_lines[0].taxes = [igst_18];

        assert_hsn_summary(assert, base_lines, false, {
            has_igst: true,
            has_gst: false,
            has_cess: false,
            nb_columns: 6,
            display_uom: false,
            items: [
                {
                    l10n_in_hsn_code: test_hsn_code_1,
                    quantity: 1.0,
                    uom: uom_unit,
                    rate: 18.0,
                    amount_untaxed: 350.0,
                    tax_amount_igst: 63.0,
                    tax_amount_cgst: 0.0,
                    tax_amount_sgst: 0.0,
                    tax_amount_cess: 0.0,
                },
                {
                    l10n_in_hsn_code: test_hsn_code_1,
                    quantity: 1.0,
                    uom: uom_unit,
                    rate: 0.0,
                    amount_untaxed: 350.0,
                    tax_amount_igst: 0.0,
                    tax_amount_cgst: 0.0,
                    tax_amount_sgst: 0.0,
                    tax_amount_cess: 0.0,
                },
            ],
        });
    });
})