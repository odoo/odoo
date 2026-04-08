import { accountTaxHelpers } from "@account/helpers/account_tax";
import { computeComboItems } from "./compute_combo_items";

/**
 * Combo suggestion helpers shared by the POS and self-order flows.
 *
 * This util has two responsibilities:
 * 1. `ComboSuggestion` computes which combo products can be built from the current order lines,
 *    how many times they can be applied, and which concrete line combinations they consume.
 * 2. `getComboChoiceLines()` formats those computed combinations for the combo-selection popups.
 */
const MAX_COMBO_COMPUTATIONS = 20;

export class ComboSuggestion {
    constructor(models, currency, company, config) {
        this.models = models;
        this.currency = currency;
        this.company = company;
        this.config = config;
        this.productCombos = this._getProductCombos();
    }

    _getProductCombos() {
        return this.models["product.product"]
            .filter((product) => product.type === "combo")
            .sort((a, b) => a.list_price - b.list_price);
    }

    _getTotalQtyAvailableByCombo(productInOrder) {
        return this.models["product.combo"]
            .flatMap((combo) => combo.combo_item_ids)
            .reduce((acc, item) => {
                const productId = item.product_id.id;
                const productQty = productInOrder[productId]?.totalQty;
                if (productQty) {
                    acc[item.combo_id.id] = (acc[item.combo_id.id] || 0) + productQty;
                }
                return acc;
            }, {});
    }

    _getLineComboData(line, comboItem, qty) {
        return {
            qty,
            combo_item: comboItem,
            line_price: line.displayPriceUnit * qty,
            display_name: line.full_product_name || line.product_id.display_name,
            attribute_value_ids: line.attribute_value_ids.map((value) => value.id),
            attribute_value_extra_price: line.attribute_value_ids.reduce(
                (sum, value) => sum + value.price_extra,
                0
            ),
        };
    }

    /**
     * Builds the concrete line selection for one combo group.
     *
     * `availableQty` is mutated on purpose to avoid reusing the same source quantities twice
     * while constructing multiple groups or multiple combinations.
     */
    _buildCombinationForGroup(order, combo, availableQty, totalQtyAvailable, comboQty) {
        const quantityTaken = {};
        let qtyNeeded = Math.min(Math.ceil(totalQtyAvailable[combo.id] / comboQty), combo.qty_max);

        for (const item of combo.combo_item_ids) {
            const productLines = availableQty[item.product_id.id]?.lines;
            if (!productLines) {
                continue;
            }

            for (const [lineUuid, qty] of Object.entries(productLines)) {
                if (qtyNeeded === 0) {
                    break;
                }
                if (qty === 0) {
                    continue;
                }

                const line = order.lines.find((orderLine) => orderLine.uuid === lineUuid);
                const takenQty = Math.min(qty, qtyNeeded);
                quantityTaken[lineUuid] = this._getLineComboData(line, item, takenQty);
                productLines[lineUuid] -= takenQty;
                qtyNeeded -= takenQty;
            }
        }

        if (combo.is_upsell) {
            quantityTaken.upsell = true;
        }

        return quantityTaken;
    }

    _buildCombinations(order, comboGroups, productInOrder, totalQtyAvailable, comboQty) {
        const combinations = [];
        const availableQty = JSON.parse(JSON.stringify(productInOrder));
        const qtyToCheck = Math.min(comboQty, MAX_COMBO_COMPUTATIONS);

        for (let i = 0; i < qtyToCheck; i++) {
            const combination = {};
            for (const combo of comboGroups) {
                combination[combo.id] = this._buildCombinationForGroup(
                    order,
                    combo,
                    availableQty,
                    totalQtyAvailable,
                    comboQty
                );
            }
            combinations.push(combination);
        }

        return combinations;
    }

    _getComboBaseLines(order, comboProduct, includedItems, extraItems) {
        const comboPrices = computeComboItems(
            comboProduct,
            includedItems,
            order.pricelist_id,
            this.models["decimal.precision"].getAll(),
            this.models["product.template.attribute.value"].getAllBy("id"),
            extraItems,
            this.currency
        );
        return comboPrices.map((comboPrice) =>
            accountTaxHelpers.prepare_base_line_for_taxes_computation(
                {},
                {
                    currency_id: this.currency,
                    quantity: comboPrice.qty,
                    price_unit: comboPrice.price_unit,
                    tax_ids: comboPrice.combo_item_id.product_id.taxes_id,
                    product_id: comboPrice.combo_item_id.product_id,
                }
            )
        );
    }

    _flattenCombinationItems(combinations) {
        return combinations
            .flatMap((items) => Object.values(items))
            .flatMap((item) => Object.values(item))
            .filter((value) => value && typeof value === "object");
    }

    /**
     * Splits combo item lines between free inclusions and paid extras for combo price computation.
     */
    _splitFreeAndExtraComboItems(itemLines) {
        const remainingFreeByCombo = new Map();
        const includedItems = [];
        const extraItems = [];

        for (const item of itemLines) {
            const comboItem = item.combo_item;
            const comboId = comboItem.combo_id.id;
            const remainingFree = remainingFreeByCombo.get(comboId) ?? comboItem.combo_id.qty_free;
            const freeQty = Math.min(item.qty, remainingFree);
            const extraQty = item.qty - freeQty;
            const baseItem = {
                combo_item_id: comboItem,
                configuration: {
                    attribute_value_ids: item.attribute_value_ids,
                    price_extra: item.attribute_value_extra_price,
                },
            };

            if (freeQty > 0) {
                includedItems.push({ ...baseItem, qty: freeQty });
            }
            if (extraQty > 0) {
                extraItems.push({ ...baseItem, qty: extraQty });
            }

            remainingFreeByCombo.set(comboId, remainingFree - freeQty);
        }

        return { includedItems, extraItems };
    }

    /**
     * Checks whether two computed combinations select the same combo items with the same attributes.
     */
    _isSameCombination(a, b) {
        const keysA = Object.keys(a);
        const keysB = Object.keys(b);

        if (keysA.length !== keysB.length) {
            return false;
        }

        for (const comboId of keysA) {
            const comboA = a[comboId];
            const comboB = b[comboId];

            if (Boolean(comboA.upsell) !== Boolean(comboB.upsell)) {
                return false;
            }

            const itemsA = Object.values(comboA).filter((v) => typeof v === "object");
            const itemsB = Object.values(comboB).filter((v) => typeof v === "object");

            if (itemsA.length !== itemsB.length) {
                return false;
            }

            for (let i = 0; i < itemsA.length; i++) {
                const itemA = itemsA[i];
                const itemB = itemsB[i];

                if (
                    itemA.combo_item.id !== itemB.combo_item.id ||
                    itemA.qty !== itemB.qty ||
                    itemA.attribute_value_ids.join(",") !== itemB.attribute_value_ids.join(",")
                ) {
                    return false;
                }
            }
        }

        return true;
    }

    /**
     * Computes the tax summary of one or more concrete combinations for a combo product.
     */
    _getCombinationsTaxSummary(order, comboProduct, combinations) {
        const baseLines = combinations.flatMap((combination) => {
            const itemLines = this._flattenCombinationItems([combination]);
            const { includedItems, extraItems } = this._splitFreeAndExtraComboItems(itemLines);
            return this._getComboBaseLines(order, comboProduct, includedItems, extraItems);
        });

        accountTaxHelpers.add_tax_details_in_base_lines(baseLines, this.company);
        accountTaxHelpers.round_base_lines_tax_details(baseLines, this.company);

        return accountTaxHelpers.get_tax_totals_summary(baseLines, this.currency, this.company, {
            cash_rounding: this.config.cash_rounding ? this.config.rounding_method : null,
        });
    }

    _getMatchingComboEntry(order, comboProduct, combinations, comboQty) {
        const itemLines = this._flattenCombinationItems(combinations);
        const taxSummary = this._getCombinationsTaxSummary(order, comboProduct, combinations);
        const totalComboPrice =
            this.config.iface_tax_included === "total"
                ? taxSummary.total_amount
                : taxSummary.base_amount;

        return {
            product: comboProduct,
            combinations,
            combinationsQty: comboQty,
            totalComboPrice,
            totalSplitedComboLinePrice: this.currency.round(
                itemLines.reduce((sum, line) => sum + line.line_price, 0)
            ),
        };
    }

    _getProductOrderMap(order) {
        const lines = order.unsentLines || order.lines;
        return lines.reduce((acc, line) => {
            if (line.isPartOfCombo() || line.qty <= 0) {
                return acc;
            }

            const productId = line.product_id.id;
            if (!acc[productId]) {
                acc[productId] = { lines: {}, totalQty: 0 };
            }

            acc[productId].lines[line.uuid] = line.qty;
            acc[productId].totalQty += line.qty;
            return acc;
        }, {});
    }

    /**
     * Computes how many times a combo can be assembled from the available standalone quantities.
     *
     * Upsell groups only affect the metadata returned to the UI; they do not block the combo from
     * being considered applicable.
     */
    _getComboAvailability(comboGroups, totalQtyAvailable) {
        let comboQty = 0;
        let hasUpsell = false;

        for (const combo of comboGroups) {
            if (combo.is_upsell) {
                hasUpsell = true;
                continue;
            }

            const availableQty = totalQtyAvailable[combo.id] || 0;
            if (availableQty < combo.qty_free) {
                return { comboQty: 0, hasUpsell };
            }
            const qtyToAdd = availableQty / combo.qty_free;
            comboQty = comboQty ? Math.min(qtyToAdd, comboQty) : qtyToAdd;
        }

        return { comboQty, hasUpsell };
    }

    /**
     * Returns the combo products that can be assembled from the current order.
     *
     * Modes:
     * - `limited`: quick existence check used when only a preview is needed.
     * - `combinations`: computes concrete combinations for suggestion and conversion flows.
     */
    getApplicableProductCombo(order, mode = "limited") {
        const matchingCombos = [];
        const productInOrder = this._getProductOrderMap(order);
        const totalQtyAvailable = this._getTotalQtyAvailableByCombo(productInOrder);

        for (const comboProduct of this.productCombos) {
            const comboGroups = comboProduct.combo_ids;
            const { comboQty, hasUpsell } = this._getComboAvailability(
                comboGroups,
                totalQtyAvailable
            );

            if (comboQty === 0) {
                continue;
            }

            if (mode === "limited") {
                matchingCombos.push({
                    product: comboProduct,
                    quantity: comboQty,
                    hasUpsell,
                });
                if (matchingCombos.length > 1) {
                    break;
                }
                continue;
            }

            const combinations = this._buildCombinations(
                order,
                comboGroups,
                productInOrder,
                totalQtyAvailable,
                comboQty
            );
            const grouped = [];

            for (const combination of combinations) {
                let found = false;

                for (const group of grouped) {
                    if (this._isSameCombination(group[0], combination)) {
                        group.push(combination);
                        found = true;
                        break;
                    }
                }

                if (!found) {
                    grouped.push([combination]);
                }
            }

            for (const group of grouped) {
                matchingCombos.push(
                    this._getMatchingComboEntry(order, comboProduct, group, group.length)
                );
            }
        }

        return matchingCombos;
    }

    getPotentialCombos(order) {
        const potentialCombos = this.getApplicableProductCombo(order, "combinations");

        potentialCombos.forEach((combo) => {
            combo.comboPrice = combo.product.getPrice(order.pricelist_id, combo.combinationsQty);
            combo.numberOfUpsell = Object.values(combo.combinations[0]).reduce(
                (acc, c) => acc + (c.upsell ? 1 : 0),
                0
            );
            combo.upsell = combo.numberOfUpsell > 0;
        });

        potentialCombos.sort((a, b) => {
            if (a.upsell !== b.upsell) {
                return a.upsell ? 1 : -1;
            }
            if (!a.upsell) {
                return b.comboPrice - a.comboPrice;
            }
            return a.numberOfUpsell === b.numberOfUpsell
                ? b.comboPrice - a.comboPrice
                : a.numberOfUpsell - b.numberOfUpsell;
        });

        return potentialCombos;
    }

    /**
     * Converts one computed combination back into the `comboValues` payload expected by combo
     * creation flows.
     */
    getComboValuesFromCombination(combination) {
        const result = [];

        for (const combo of Object.values(combination)) {
            if (!combo) {
                continue;
            }

            for (const item of Object.values(combo)) {
                if (!item || typeof item !== "object" || item.qty <= 0) {
                    continue;
                }

                result.push({
                    combo_item_id: item.combo_item,
                    qty: item.qty,
                    configuration: {
                        attribute_custom_values: [],
                        attribute_value_ids: item.attribute_value_ids,
                        price_extra: item.attribute_value_extra_price,
                    },
                });
            }
        }

        return result;
    }

    sortComboChoiceLines(lines) {
        return lines.sort((a, b) => {
            if (a.upsell !== b.upsell) {
                return a.upsell ? 1 : -1;
            }
            if (a.sequence !== b.sequence) {
                return a.sequence - b.sequence;
            }
            return a.id - b.id;
        });
    }

    getOrCreateChoiceEntry(comboItems, name, comboProduct, upsell = false) {
        if (!comboItems[name]) {
            comboItems[name] = {
                quantity: 0,
                upsell,
                sequence: comboProduct.sequence,
                id: comboProduct.id,
            };
        }
        return comboItems[name];
    }

    /**
     * Formats one combination into readable choice lines for the combo suggestion dialog.
     *
     * Upsell placeholders are represented as synthetic lines when a combo group still has remaining
     * capacity that would need an extra paid item.
     */
    getComboChoiceLines(combinations) {
        const comboItems = {};
        const comboList = Array.isArray(combinations) ? combinations : [combinations];

        for (const combination of comboList) {
            for (const [comboId, comboChoice] of Object.entries(combination)) {
                const comboProduct = this.models["product.combo"].get(comboId);
                const totalChosenQty = Object.values(comboChoice).reduce(
                    (sum, line) =>
                        line === true || typeof line === "number" ? sum : sum + line.qty,
                    0
                );

                for (const line of Object.values(comboChoice)) {
                    // `true` marks an upsell placeholder.
                    if (line === true) {
                        if (totalChosenQty < comboProduct.qty_max) {
                            const choice = this.getOrCreateChoiceEntry(
                                comboItems,
                                comboProduct.name,
                                comboProduct,
                                true
                            );
                            choice.quantity += comboProduct.qty_max - totalChosenQty;
                        }
                        continue;
                    }

                    const choice = this.getOrCreateChoiceEntry(
                        comboItems,
                        line.display_name || line.combo_item.product_id.display_name,
                        comboProduct
                    );
                    choice.quantity += line.qty;
                }
            }
        }

        return this.sortComboChoiceLines(
            Object.entries(comboItems).map(([name, value]) => ({
                name,
                ...value,
            }))
        );
    }
}
