import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    can_be_merged_with(orderline) {
        // The Blackbox doesn't allow lines with a quantity of 5 numbers.
        if (
            !this.order_id.useBlackBoxBe() ||
            (this.order_id.useBlackBoxBe() && this.get_quantity() < 9999)
        ) {
            return super.can_be_merged_with(orderline);
        }
        return false;
    },
    _generateTranslationTable() {
        const replacements = [
            ["ÄÅÂÁÀâäáàã", "A"],
            ["Ææ", "AE"],
            ["ß", "SS"],
            ["çÇ", "C"],
            ["ÎÏÍÌïîìí", "I"],
            ["€", "E"],
            ["ÊËÉÈêëéè", "E"],
            ["ÛÜÚÙüûúù", "U"],
            ["ÔÖÓÒöôóò", "O"],
            ["Œœ", "OE"],
            ["ñÑ", "N"],
            ["ýÝÿ", "Y"],
        ];

        const lowercaseAsciiStart = "a".charCodeAt(0);
        const lowercaseAsciiEnd = "z".charCodeAt(0);

        for (
            let lowercaseAsciiCode = lowercaseAsciiStart;
            lowercaseAsciiCode <= lowercaseAsciiEnd;
            lowercaseAsciiCode++
        ) {
            const lowercaseChar = String.fromCharCode(lowercaseAsciiCode);
            const uppercaseChar = lowercaseChar.toUpperCase();
            replacements.push([lowercaseChar, uppercaseChar]);
        }

        const lookupTable = {};
        for (let i = 0; i < replacements.length; i++) {
            const letterGroup = replacements[i];
            const specialChars = letterGroup[0];
            const uppercaseReplacement = letterGroup[1];

            for (let j = 0; j < specialChars.length; j++) {
                const specialChar = specialChars[j];
                lookupTable[specialChar] = uppercaseReplacement;
            }
        }

        return lookupTable;
    },
    generatePluLine() {
        // |--------+-------------+-------+-----|
        // | AMOUNT | DESCRIPTION | PRICE | VAT |
        // |      4 |          20 |     8 |   1 |
        // |--------+-------------+-------+-----|

        // steps:
        // 1. replace all chars
        // 2. filter out forbidden chars
        // 3. build PLU line

        let amount = this._getAmountForPlu();
        let description = this.get_product().display_name;
        let price_in_eurocent = this.get_display_price() * 100;
        const tax_labels = this.getLineTaxLabels();

        amount = this._prepareNumberForPlu(amount, 4);
        description = this._prepareDescriptionForPlu(description);
        price_in_eurocent = this._prepareNumberForPlu(price_in_eurocent, 8);

        return amount + description + price_in_eurocent + tax_labels;
    },
    _prepareNumberForPlu(number, field_length) {
        number = Math.abs(number);
        number = Math.round(number);

        let number_string = number.toFixed(0);

        number_string = this._replaceHashAndSignChars(number_string);
        number_string = this._filterAllowedHashAndSignChars(number_string);

        // get the required amount of least significant characters
        number_string = number_string.substr(-field_length);

        // pad left with 0 to required size
        while (number_string.length < field_length) {
            number_string = "0" + number_string;
        }

        return number_string;
    },
    _prepareDescriptionForPlu(description) {
        description = this._replaceHashAndSignChars(description);
        description = this._filterAllowedHashAndSignChars(description);

        // get the 20 most significant characters
        description = description.substr(0, 20);

        // pad right with SPACE to required size of 20
        while (description.length < 20) {
            description = description + " ";
        }

        return description;
    },
    _getAmountForPlu() {
        let amount = this.get_quantity();
        const uom = this.get_unit();

        if (uom.is_unit) {
            return amount;
        } else {
            if (uom.category_id[1] === "Weight") {
                const uom_gram = this.models["uom.uom"].find(
                    (uom) => uom.category_id.name === "Weight" && uom.name === "g"
                );
                if (uom_gram) {
                    amount = (amount / uom.factor) * uom_gram.factor;
                }
            } else if (uom.category_id[1] === "Volume") {
                const uom_milliliter = this.models["uom.uom"].find(
                    (uom) => uom.category_id.name === "Volume" && uom.name === "Milliliter(s)"
                );
                if (uom_milliliter) {
                    amount = (amount / uom.factor) * uom_milliliter.factor;
                }
            }

            return amount;
        }
    },
    _replaceHashAndSignChars(str) {
        if (typeof str !== "string") {
            throw "Can only handle strings";
        }

        const translationTable = this._generateTranslationTable();

        const replaced_char_array = str.split("").map((char) => {
            const translation = translationTable[char];
            return translation !== undefined ? translation : char;
        });

        return replaced_char_array.join("");
    },
    // for hash and sign the allowed range for DATA is:
    //   - A-Z
    //   - 0-9
    // and SPACE as well. We filter SPACE out here though, because
    // SPACE will only be used in DATA of hash and sign as description
    // padding
    _filterAllowedHashAndSignChars(str) {
        if (typeof str !== "string") {
            throw "Can only handle strings";
        }

        const filtered_char_array = str.split("").filter((char) => {
            const ascii_code = char.charCodeAt(0);

            if (
                (ascii_code >= "A".charCodeAt(0) && ascii_code <= "Z".charCodeAt(0)) ||
                (ascii_code >= "0".charCodeAt(0) && ascii_code <= "9".charCodeAt(0))
            ) {
                return true;
            } else {
                return false;
            }
        });

        return filtered_char_array.join("");
    },
    getLineTaxLabels() {
        return this.product_id.taxes_id?.map((tax) => tax.tax_group_id.pos_receipt_label).join(" ");
    },
    setOptions(options) {
        super.setOptions(...arguments);
        if (options.qty_sign) {
            this.set_quantity(this.get_quantity() * options.qty_sign);
        }
    },
});
