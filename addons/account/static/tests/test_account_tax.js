/** @odoo-module **/

import {
    adapt_price_unit_to_another_taxes,
    computeSingleLineTaxes,
    eval_taxes_computation_prepare_context,
} from "@account/helpers/account_tax";
import { roundPrecision } from "@web/core/utils/numbers";

let number = 0;

export function common_kwargs() {
    number += 1;
    return {
        id: number,
        name: `${number}`,
        sequence: 10,
        tax_exigibility: "on_invoice",
        price_include: false,
        include_base_amount: false,
        is_base_affected: true,
        _invoice_repartition_line_ids: [1.0],
        _refund_repartition_line_ids: [1.0],
        _factor: 1.0,
        _invoice_base_tag_ids: [],
        _refund_base_tag_ids: [],
    }
}

export function group_of_taxes(taxes, kwargs={}) {
    return {
        ...common_kwargs(),
        ...kwargs,
        amount_type: "group",
        _children_tax_ids: taxes.map(tax_values => Object.assign({group_id: number}, tax_values)),
    }
}

export function percent_tax(amount, kwargs={}) {
    return {
        ...common_kwargs(),
        ...kwargs,
        amount_type: "percent",
        amount: amount,
    }
}

export function division_tax(amount, kwargs={}) {
    return {
        ...common_kwargs(),
        ...kwargs,
        amount_type: "division",
        amount: amount,
    }
}

export function fixed_tax(amount, kwargs={}) {
    return {
        ...common_kwargs(),
        ...kwargs,
        amount_type: "fixed",
        amount: amount,
    }
}

export function checkTaxResults(assert, taxes, expectedValues, priceUnit, evaluationContextKwargs={}, computeKwargs={}) {
    const compare_values = function (results, expectedValues, rounding) {
        assert.strictEqual(
            roundPrecision(results.total_included, rounding),
            roundPrecision(expectedValues.total_included, rounding),
        );
        assert.strictEqual(
            roundPrecision(results.total_excluded, rounding),
            roundPrecision(expectedValues.total_excluded, rounding),
        );
        assert.strictEqual(results.tax_values_list.length, expectedValues.tax_values_list.length);
        for (const [i, expectedTaxValues] of expectedValues.tax_values_list.entries()) {
            const taxValues = results.tax_values_list[i];
            assert.strictEqual(
                roundPrecision(taxValues.base, rounding),
                roundPrecision(expectedTaxValues[0], rounding),
            );
            assert.strictEqual(
                roundPrecision(taxValues.tax_amount_factorized, rounding),
                roundPrecision(expectedTaxValues[1], rounding),
            );
        }
    }

    const quantity = evaluationContextKwargs.hasOwnProperty("quantity") ? evaluationContextKwargs.quantity : 1;
    let evaluationContext = eval_taxes_computation_prepare_context(priceUnit, quantity, evaluationContextKwargs);
    let results = computeSingleLineTaxes(taxes, evaluationContext, computeKwargs);
    const isRoundGlobally = evaluationContext.rounding_method === "round_globally";
    const rounding = isRoundGlobally ? 0.000001 : 0.01;
    compare_values(results, expectedValues, rounding);

    if (isRoundGlobally) {
        let evaluationContext = eval_taxes_computation_prepare_context(results.total_excluded, quantity, Object.assign(
            {reverse: true},
            evaluationContextKwargs,
        ));
        results = computeSingleLineTaxes(taxes, evaluationContext, computeKwargs);
        compare_values(results, expectedValues, rounding);
        let delta = 0.0;
        for(const tax_values of results.tax_values_list){
            if(tax_values.price_include){
                delta += tax_values.tax_amount_factorized;
            }
        }
        assert.strictEqual(
            roundPrecision(results.total_excluded + delta, rounding),
            roundPrecision(priceUnit, rounding),
        );
    }
}

QUnit.module("test_account_tax", ({}) => {

    QUnit.test("test_taxes_ordering", async (assert) => {
        assert.expect(9);
        const tax_division = division_tax(10.0, {sequence: 1});
        const tax_fixed = fixed_tax(10.0, {sequence: 2});
        const tax_percent = percent_tax(10.0, {sequence: 3});
        const tax_group = group_of_taxes([tax_fixed, tax_percent], {sequence: 4});
        checkTaxResults(
            assert,
            [tax_group, tax_division],
            {
                total_included: 252.22,
                total_excluded: 200.0,
                tax_values_list: [
                    [200.0, 22.22],
                    [200.0, 10.0],
                    [200.0, 20.0],
                ],
            },
            200.0,
        );
    });

    QUnit.test("test_random_case_1", async (assert) => {
        assert.expect(22);
        const tax_percent_8_price_included = percent_tax(8.0, {price_include: true});
        const tax_percent_0_price_included = percent_tax(0.0, {price_include: true});

        checkTaxResults(
            assert,
            [tax_percent_8_price_included, tax_percent_0_price_included],
            {
                total_included: 124.40,
                total_excluded: 115.19,
                tax_values_list: [
                    [115.19, 9.21],
                    [115.19, 0.0],
                ],
            },
            124.40,
            {rounding_method: "round_per_line"},
        );

        checkTaxResults(
            assert,
            [tax_percent_8_price_included, tax_percent_0_price_included],
            {
                total_included: 124.40,
                total_excluded: 115.185185,
                tax_values_list: [
                    [115.185185, 9.214815],
                    [115.185185, 0.0],
                ],
            },
            124.40,
            {rounding_method: "round_globally"},
        );
    });

    QUnit.test("test_random_case_2", async (assert) => {
        assert.expect(48);
        const tax_percent_5_price_included = percent_tax(5.0, {price_include: true});
        const currency_dp_half = 0.05;

        checkTaxResults(
            assert,
            [tax_percent_5_price_included],
            {
                total_included: 5.0,
                total_excluded: 4.75,
                tax_values_list: [
                    [4.75, 0.25],
                ],
            },
            5.0,
            {rounding_method: "round_per_line", precision_rounding: currency_dp_half},
        );
        checkTaxResults(
            assert,
            [tax_percent_5_price_included],
            {
                total_included: 10.0,
                total_excluded: 9.5,
                tax_values_list: [
                    [9.5, 0.5],
                ],
            },
            10.0,
            {rounding_method: "round_per_line", precision_rounding: currency_dp_half},
        );
        checkTaxResults(
            assert,
            [tax_percent_5_price_included],
            {
                total_included: 50.0,
                total_excluded: 47.6,
                tax_values_list: [
                    [47.6, 2.4],
                ],
            },
            50.0,
            {rounding_method: "round_per_line", precision_rounding: currency_dp_half},
        );

        checkTaxResults(
            assert,
            [tax_percent_5_price_included],
            {
                total_included: 5.0,
                total_excluded: 4.761905,
                tax_values_list: [
                    [4.761905, 0.238095],
                ],
            },
            5.0,
            {rounding_method: "round_globally"},
        );
        checkTaxResults(
            assert,
            [tax_percent_5_price_included],
            {
                total_included: 10.0,
                total_excluded: 9.52381,
                tax_values_list: [
                    [9.52381, 0.47619],
                ],
            },
            10.0,
            {rounding_method: "round_globally"},
        );
        checkTaxResults(
            assert,
            [tax_percent_5_price_included],
            {
                total_included: 50.0,
                total_excluded: 47.619048,
                tax_values_list: [
                    [47.619048, 2.380952],
                ],
            },
            50.0,
            {rounding_method: "round_globally"},
        );
    });

    QUnit.test("test_random_case_3", async (assert) => {
        assert.expect(22);
        const tax_percent_15_price_excluded = percent_tax(15.0);
        const tax_percent_5_5_price_included = percent_tax(5.5, {price_include: true});

        checkTaxResults(
            assert,
            [tax_percent_15_price_excluded, tax_percent_5_5_price_included],
            {
                total_included: 2627.01,
                total_excluded: 2180.09,
                tax_values_list: [
                    [2180.09, 327.01],
                    [2180.09, 119.91],
                ],
            },
            2300.0,
            {rounding_method: "round_per_line"},
        );

        checkTaxResults(
            assert,
            [tax_percent_15_price_excluded, tax_percent_5_5_price_included],
            {
                total_included: 2627.014218,
                total_excluded: 2180.094787,
                tax_values_list: [
                    [2180.094787, 327.014218],
                    [2180.094787, 119.905213],
                ],
            },
            2300.0,
            {rounding_method: "round_globally"},
        );
    });

    QUnit.test("test_random_case_4", async (assert) => {
        assert.expect(16);
        const tax_percent_12_price_included = percent_tax(12.0, {price_include: true});

        checkTaxResults(
            assert,
            [tax_percent_12_price_included],
            {
                total_included: 52.50,
                total_excluded: 46.87,
                tax_values_list: [
                    [46.87, 5.63],
                ],
            },
            52.50,
            {rounding_method: "round_per_line"},
        );

        checkTaxResults(
            assert,
            [tax_percent_12_price_included],
            {
                total_included: 52.50,
                total_excluded: 46.875,
                tax_values_list: [
                    [46.875, 5.625],
                ],
            },
            52.50,
            {rounding_method: "round_globally"},
        );
    });

    QUnit.test("test_random_case_5", async (assert) => {
        assert.expect(64);
        const tax_percent_19 = percent_tax(19.0);
        const tax_percent_19_price_included = percent_tax(19.0, { price_include: true });
        const currency_dp_0 = 1.0;

        checkTaxResults(
            assert,
            [tax_percent_19],
            {
                total_included: 27000.0,
                total_excluded: 22689.0,
                tax_values_list: [
                    [22689, 4311],
                ],
            },
            22689.0,
            {rounding_method: "round_per_line", precision_rounding: currency_dp_0},
        );

        checkTaxResults(
            assert,
            [tax_percent_19],
            {
                total_included: 10919.0,
                total_excluded: 9176.0,
                tax_values_list: [
                    [9176, 1743],
                ],
            },
            9176.0,
            {rounding_method: "round_per_line", precision_rounding: currency_dp_0},
        );

        checkTaxResults(
            assert,
            [tax_percent_19_price_included],
            {
                total_included: 27000.0,
                total_excluded: 22689.0,
                tax_values_list: [
                    [22689.0, 4311.0],
                ],
            },
            27000.0,
            {rounding_method: "round_per_line", precision_rounding: currency_dp_0},
        );

        checkTaxResults(
            assert,
            [tax_percent_19_price_included],
            {
                total_included: 10920.0,
                total_excluded: 9176.0,
                tax_values_list: [
                    [9176.0, 1744.0],
                ],
            },
            10920.0,
            {rounding_method: "round_per_line", precision_rounding: currency_dp_0},
        );

        checkTaxResults(
            assert,
            [tax_percent_19],
            {
                total_included: 26999.91,
                total_excluded: 22689.0,
                tax_values_list: [
                    [22689, 4310.91],
                ],
            },
            22689.0,
            {rounding_method: "round_globally"},
        );

        checkTaxResults(
            assert,
            [tax_percent_19],
            {
                total_included: 10919.44,
                total_excluded: 9176.0,
                tax_values_list: [
                    [9176, 1743.44],
                ],
            },
            9176.0,
            {rounding_method: "round_globally"},
        );

        checkTaxResults(
            assert,
            [tax_percent_19_price_included],
            {
                total_included: 27000.0,
                total_excluded: 22689.07563,
                tax_values_list: [
                    [22689.07563, 4310.92437],
                ],
            },
            27000.0,
            {rounding_method: "round_globally"},
        );

        checkTaxResults(
            assert,
            [tax_percent_19_price_included],
            {
                total_included: 10920.0,
                total_excluded: 9176.470588,
                tax_values_list: [
                    [9176.470588, 1743.529412],
                ],
            },
            10920.0,
            {rounding_method: "round_globally"},
        );
    });

    QUnit.test("test_random_case_6", async (assert) => {
        assert.expect(16);
        const tax_percent_20_price_included = percent_tax(20.0, { price_include: true });
        const currency_dp_6 = 0.000001;

        checkTaxResults(
            assert,
            [tax_percent_20_price_included],
            {
                total_included: 399.999999,
                total_excluded: 333.333332,
                tax_values_list: [
                    [333.333332, 66.666667],
                ],
            },
            399.999999,
            {rounding_method: "round_per_line", precision_rounding: currency_dp_6},
        );

        checkTaxResults(
            assert,
            [tax_percent_20_price_included],
            {
                total_included: 399.999999,
                total_excluded: 333.3333325,
                tax_values_list: [
                    [333.3333325, 66.6666665],
                ],
            },
            399.999999,
            {rounding_method: "round_globally"},
        );
    });

    QUnit.test("test_random_case_7", async (assert) => {
        assert.expect(48);
        const tax_percent_21_price_included = percent_tax(21.0, { price_include: true });
        const currency_dp_6 = 0.000001;

        checkTaxResults(
            assert,
            [tax_percent_21_price_included],
            {
                total_included: 11.90,
                total_excluded: 9.83,
                tax_values_list: [
                    [9.83, 2.07],
                ],
            },
            11.90,
            {rounding_method: "round_per_line"},
        );

        checkTaxResults(
            assert,
            [tax_percent_21_price_included],
            {
                total_included: 2.80,
                total_excluded: 2.31,
                tax_values_list: [
                    [2.31, 0.49],
                ],
            },
            2.80,
            {rounding_method: "round_per_line"},
        );

        checkTaxResults(
            assert,
            [tax_percent_21_price_included],
            {
                total_included: 7.0,
                total_excluded: 5.785124,
                tax_values_list: [
                    [5.785124, 1.214876],
                ],
            },
            7.0,
            {rounding_method: "round_per_line", precision_rounding: currency_dp_6},
        );

        checkTaxResults(
            assert,
            [tax_percent_21_price_included],
            {
                total_included: 11.90,
                total_excluded: 9.834711,
                tax_values_list: [
                    [9.834711, 2.065289],
                ],
            },
            11.90,
            {rounding_method: "round_globally"},
        );

        checkTaxResults(
            assert,
            [tax_percent_21_price_included],
            {
                total_included: 2.80,
                total_excluded: 2.31405,
                tax_values_list: [
                    [2.31405, 0.48595],
                ],
            },
            2.80,
            {rounding_method: "round_globally"},
        );

        checkTaxResults(
            assert,
            [tax_percent_21_price_included],
            {
                total_included: 7.0,
                total_excluded: 5.785124,
                tax_values_list: [
                    [5.785124, 1.214876],
                ],
            },
            7.0,
            {rounding_method: "round_globally"},
        );
    });

    QUnit.test("test_random_case_8", async (assert) => {
        assert.expect(9);
        const tax_percent_20_withholding = percent_tax(-20.0);
        const tax_percent_4 = percent_tax(4.0, { include_base_amount: true });
        const tax_percent_22 = percent_tax(22.0);

        checkTaxResults(
            assert,
            [tax_percent_20_withholding, tax_percent_4, tax_percent_22],
            {
                total_included: 53.44,
                total_excluded: 50.0,
                tax_values_list: [
                    [50.0, -10.0],
                    [50.0, 2.0],
                    [52.0, 11.44],
                ],
            },
            50.0,
        );
    });

    QUnit.test("test_fixed_tax_price_included_affect_base_on_0", async (assert) => {
        assert.expect(5);
        const tax = fixed_tax(0.05, { price_include: true, include_base_amount: true });

        checkTaxResults(
            assert,
            [tax],
            {
                total_included: 0.0,
                total_excluded: -0.05,
                tax_values_list: [
                    [-0.05, 0.05],
                ],
            },
            0.0,
        );
    });

    QUnit.test("test_percent_taxes_for_l10n_in", async (assert) => {
        assert.expect(71);
        const tax1 = percent_tax(6);
        const tax2 = percent_tax(6);
        const tax3 = percent_tax(3);

        checkTaxResults(
            assert,
            [tax1, tax2, tax3],
            {
                total_included: 115.0,
                total_excluded: 100.0,
                tax_values_list: [
                    [100.0, 6.0],
                    [100.0, 6.0],
                    [100.0, 3.0],
                ],
            },
            100.0,
        );

        // tax       price_incl      incl_base_amount    is_base_affected
        // ----------------------------------------------------------------
        // tax1                      T                   T
        // tax2                                          T
        // tax3                                          T
        tax1.include_base_amount = true;
        checkTaxResults(
            assert,
            [tax1, tax2, tax3],
            {
                total_included: 115.54,
                total_excluded: 100.0,
                tax_values_list: [
                    [100.0, 6.0],
                    [106.0, 6.36],
                    [106.0, 3.18],
                ],
            },
            100.0,
        );

        // tax       price_incl      incl_base_amount    is_base_affected
        // ----------------------------------------------------------------
        // tax1                      T                   T
        // tax2                      T                   T
        // tax3                                          T
        tax2.include_base_amount = true;
        checkTaxResults(
            assert,
            [tax1, tax2, tax3],
            {
                total_included: 115.73,
                total_excluded: 100.0,
                tax_values_list: [
                    [100.0, 6.0],
                    [106.0, 6.36],
                    [112.36, 3.37],
                ],
            },
            100.0,
        );

        // tax       price_incl      incl_base_amount    is_base_affected
        // ----------------------------------------------------------------
        // tax1                      T                   T
        // tax2                      T
        // tax3                                          T
        tax2.is_base_affected = false;
        checkTaxResults(
            assert,
            [tax1, tax2, tax3],
            {
                total_included: 115.36,
                total_excluded: 100.0,
                tax_values_list: [
                    [100.0, 6.0],
                    [100.0, 6.0],
                    [112.0, 3.36],
                ],
            },
            100.0,
        );
        // Test the reverse.
        checkTaxResults(
            assert,
            [tax1, tax2, tax3],
            {
                total_included: 115.36,
                total_excluded: 100.0,
                tax_values_list: [
                    [100.0, 6.0],
                    [100.0, 6.0],
                    [112.0, 3.36],
                ],
            },
            100.0,
            {rounding_method: "round_globally"},
        );

        // tax       price_incl      incl_base_amount    is_base_affected
        // ----------------------------------------------------------------
        // tax1      T               T                   T
        // tax2      T               T
        // tax3                                          T
        tax1.price_include = true;
        tax2.price_include = true;
        checkTaxResults(
            assert,
            [tax1, tax2, tax3],
            {
                total_included: 115.36,
                total_excluded: 100.0,
                tax_values_list: [
                    [100.0, 6.0],
                    [100.0, 6.0],
                    [112.0, 3.36],
                ],
            },
            112.0,
        );

        // Ensure tax1 & tax2 give always the same result.
        checkTaxResults(
            assert,
            [tax1, tax2],
            {
                total_included: 17.79,
                total_excluded: 15.89,
                tax_values_list: [
                    [15.89, 0.95],
                    [15.89, 0.95],
                ],
            },
            17.79,
        );
    });

    QUnit.test("test_division_taxes_for_l10n_br", async (assert) => {
        assert.expect(106);
        const tax1 = division_tax(5);
        const tax2 = division_tax(3);
        const tax3 = division_tax(0.65);
        const tax4 = division_tax(9);
        const tax5 = division_tax(15);

        // Same of tax4/tax5 except the amount is based on 32% of the base amount.
        const tax4_32 = division_tax(9);
        const tax5_32 = division_tax(15);
        tax4_32._factor = 0.32;
        tax5_32._factor = 0.32;

        checkTaxResults(
            assert,
            [tax1, tax2, tax3, tax4, tax5],
            {
                total_included: 48.0,
                total_excluded: 32.33,
                tax_values_list: [
                    [32.33, 2.4],
                    [32.33, 1.44],
                    [32.33, 0.31],
                    [32.33, 4.32],
                    [32.33, 7.2],
                ],
            },
            32.33,
        );
        checkTaxResults(
            assert,
            [tax1, tax2, tax3, tax4_32, tax5_32],
            {
                total_included: 1000.0,
                total_excluded: 836.7,
                tax_values_list: [
                    [836.7, 50.0],
                    [836.7, 30.0],
                    [836.7, 6.5],
                    [836.7, 28.8],
                    [836.7, 48.0],
                ],
            },
            836.7,
        );

        tax1.price_include = true;
        tax2.price_include = true;
        tax3.price_include = true;
        tax4.price_include = true;
        tax5.price_include = true;
        checkTaxResults(
            assert,
            [tax1, tax2, tax3, tax4, tax5],
            {
                total_included: 48.0,
                total_excluded: 32.33,
                tax_values_list: [
                    [32.33, 2.4],
                    [32.33, 1.44],
                    [32.33, 0.31],
                    [32.33, 4.32],
                    [32.33, 7.2],
                ],
            },
            48.0,
        );
        tax4_32.price_include = true;
        tax5_32.price_include = true;
        checkTaxResults(
            assert,
            [tax1, tax2, tax3, tax4_32, tax5_32],
            {
                total_included: 1000.0,
                total_excluded: 836.7,
                tax_values_list: [
                    [836.7, 50.0],
                    [836.7, 30.0],
                    [836.7, 6.5],
                    [836.7, 28.8],
                    [836.7, 48.0],
                ],
            },
            1000.0,
        );

        // Test the reverse:
        checkTaxResults(
            assert,
            [tax1, tax2, tax3, tax4, tax5],
            {
                total_included: 48.0,
                total_excluded: 32.3279999,
                tax_values_list: [
                    [32.3279999, 2.4],
                    [32.3279999, 1.44],
                    [32.3279999, 0.312],
                    [32.3279999, 4.32],
                    [32.3279999, 7.2],
                ],
            },
            48.0,
            {rounding_method: "round_globally"},
        );
        checkTaxResults(
            assert,
            [tax1, tax2, tax3, tax4_32, tax5_32],
            {
                total_included: 1000.0,
                total_excluded: 836.7,
                tax_values_list: [
                    [836.7, 50.0],
                    [836.7, 30.0],
                    [836.7, 6.5],
                    [836.7, 28.8],
                    [836.7, 48.0],
                ],
            },
            1000.0,
            {rounding_method: "round_globally"},
        );
    });


    QUnit.test("test_fixed_taxes_for_l10n_be", async (assert) => {
        assert.expect(63);
        const tax1 = fixed_tax(1);
        const tax2 = percent_tax(21);
        const tax3 = fixed_tax(2);

        checkTaxResults(
            assert,
            [tax1, tax2, tax3],
            {
                total_included: 136.0,
                total_excluded: 100.0,
                tax_values_list: [
                    [100.0, 5.0],
                    [100.0, 21.0],
                    [100.0, 10.0],
                ],
            },
            20.0,
            { quantity: 5 }
        );

        // tax       price_incl      incl_base_amount
        // -----------------------------------------------
        // tax1                      T
        // tax2
        // tax3
        tax1.include_base_amount = true;
        checkTaxResults(
            assert,
            [tax1, tax2, tax3],
            {
                total_included: 131.0,
                total_excluded: 95.0,
                tax_values_list: [
                    [95.0, 5.0],
                    [100.0, 21.0],
                    [100.0, 10.0],
                ],
            },
            19.0,
            { quantity: 5 },
        );

        // tax       price_incl      incl_base_amount
        // -----------------------------------------------
        // tax1                      T
        // tax2      T
        // tax3
        tax2.price_include = true;
        checkTaxResults(
            assert,
            [tax1, tax2, tax3],
            {
                total_included: 123.0,
                total_excluded: 99.0,
                tax_values_list: [
                    [99.0, 1.0],
                    [100.0, 21.0],
                    [121.0, 2.0],
                ],
            },
            120.0,
        );

        // tax       price_incl      incl_base_amount
        // -----------------------------------------------
        // tax1                      T
        // tax2      T               T
        // tax3
        tax2.include_base_amount = true;
        checkTaxResults(
            assert,
            [tax1, tax2, tax3],
            {
                total_included: 123.0,
                total_excluded: 99.0,
                tax_values_list: [
                    [99.0, 1.0],
                    [100.0, 21.0],
                    [121.0, 2.0],
                ],
            },
            120.0,
        );

        // tax       price_incl      incl_base_amount
        // -----------------------------------------------
        // tax1
        // tax2      T               T
        // tax3
        tax1.include_base_amount = false;
        checkTaxResults(
            assert,
            [tax1, tax2, tax3],
            {
                total_included: 124.0,
                total_excluded: 100.0,
                tax_values_list: [
                    [100.0, 1.0],
                    [100.0, 21.0],
                    [121.0, 2.0],
                ],
            },
            121.0,
        );

        // tax       price_incl      incl_base_amount
        // -----------------------------------------------
        // tax1      T
        // tax2      T               T
        // tax3
        tax1.price_include = true;
        checkTaxResults(
            assert,
            [tax1, tax2, tax3],
            {
                total_included: 123.0,
                total_excluded: 99.0,
                tax_values_list: [
                    [99.0, 1.0],
                    [100.0, 21.0],
                    [121.0, 2.0],
                ],
            },
            121.0,
        );

        // tax       price_incl      incl_base_amount
        // -----------------------------------------------
        // tax1      T               T
        // tax2      T               T
        // tax3
        tax1.include_base_amount = true;
        checkTaxResults(
            assert,
            [tax1, tax2, tax3],
            {
                total_included: 123.0,
                total_excluded: 99.0,
                tax_values_list: [
                    [99.0, 1.0],
                    [100.0, 21.0],
                    [121.0, 2.0],
                ],
            },
            121.0,
        );
    });

    QUnit.test("test_adapt_price_unit_to_another_taxes", async (assert) => {
        assert.expect(6);
        const tax_fixed_incl = fixed_tax(10, { price_include: true });
        const tax_fixed_excl = fixed_tax(10);
        const tax_include_src = percent_tax(21, { price_include: true });
        const tax_include_dst = percent_tax(6, { price_include: true });
        const tax_exclude_src = percent_tax(15);
        const tax_exclude_dst = percent_tax(21);

        let product_price_unit = adapt_price_unit_to_another_taxes(
            121.0,
            [tax_include_src],
            [tax_include_dst],
        );
        assert.strictEqual(product_price_unit, 106.0);

        product_price_unit = adapt_price_unit_to_another_taxes(
            100.0,
            [tax_exclude_src],
            [tax_include_dst],
        );
        assert.strictEqual(product_price_unit, 100.0);

        product_price_unit = adapt_price_unit_to_another_taxes(
            121.0,
            [tax_include_src],
            [tax_exclude_dst],
        );
        assert.strictEqual(product_price_unit, 100.0);

        product_price_unit = adapt_price_unit_to_another_taxes(
            100.0,
            [tax_exclude_src],
            [tax_exclude_dst],
        );
        assert.strictEqual(product_price_unit, 100.0);

        product_price_unit = adapt_price_unit_to_another_taxes(
            100.0,
            [tax_fixed_incl, tax_exclude_src],
            [tax_include_dst],
        );
        assert.strictEqual(product_price_unit, 100.0);

        product_price_unit = adapt_price_unit_to_another_taxes(
            100.0,
            [tax_fixed_excl, tax_include_src],
            [tax_exclude_dst],
        );
        assert.strictEqual(product_price_unit, 100.0);
    });
});
