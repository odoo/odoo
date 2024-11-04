export class BarcodeParser {
    static barcodeNomenclatureFields = ["name", "rule_ids", "upc_ean_conv"];
    static barcodeRuleFields = ["name", "sequence", "type", "encoding", "pattern", "alias"];
    static async fetchNomenclature(orm, id) {
        const [nomenclature] = await orm.read(
            "barcode.nomenclature",
            [id],
            this.barcodeNomenclatureFields
        );
        let rules = await orm.searchRead(
            "barcode.rule",
            [["barcode_nomenclature_id", "=", id]],
            this.barcodeRuleFields
        );
        rules = rules.sort((a, b) => {
            return a.sequence - b.sequence;
        });
        nomenclature.rules = rules;
        return nomenclature;
    }

    constructor() {
        this.setup(...arguments);
    }

    setup({ nomenclature }) {
        this.nomenclature = nomenclature;
    }

    /**
     * This algorithm is identical for all fixed length numeric GS1 data structures.
     *
     * It is also valid for EAN-8, EAN-12 (UPC-A), EAN-13 check digit after sanitizing.
     * https://www.gs1.org/sites/default/files/docs/barcodes/GS1_General_Specifications.pdf
     *
     * @param {String} numericBarcode Need to have a length of 18
     * @returns {number} Check Digit
     */
    get_barcode_check_digit(numericBarcode) {
        let oddsum = 0, evensum = 0, total = 0;
        // Reverses the barcode to be sure each digit will be in the right place
        // regardless the barcode length.
        const code = numericBarcode.split('').reverse();
        // Removes the last barcode digit (should not be took in account for its own computing).
        code.shift();

        // Multiply value of each position by
        // N1  N2  N3  N4  N5  N6  N7  N8  N9  N10 N11 N12 N13 N14 N15 N16 N17 N18
        // x3  X1  x3  x1  x3  x1  x3  x1  x3  x1  x3  x1  x3  x1  x3  x1  x3  CHECK_DIGIT
        for (let i = 0; i < code.length; i++) {
            if (i % 2 === 0) {
                evensum += parseInt(code[i]);
            } else {
                oddsum += parseInt(code[i]);
            }
        }
        total = evensum * 3 + oddsum;
        return (10 - total % 10) % 10;
    }

    /**
     * Checks if the barcode string is encoded with the provided encoding.
     *
     * @param {String} barcode
     * @param {String} encoding could be 'any' (no encoding rules), 'ean8', 'upca' or 'ean13'
     * @returns {boolean}
     */
    check_encoding(barcode, encoding) {
        if (encoding === 'any') {
            return true;
        }
        const barcodeSizes = {
            ean8: 8,
            ean13: 13,
            upca: 12,
        };
        return barcode.length === barcodeSizes[encoding] && /^\d+$/.test(barcode) &&
            this.get_barcode_check_digit(barcode) === parseInt(barcode[barcode.length - 1]);
    }

    /**
     * Sanitizes a EAN-13 prefix by padding it with chars zero.
     *
     * @param {String} ean
     * @returns {String}
     */
    sanitize_ean(ean) {
        ean = ean.substr(0, 13);
        ean = "0".repeat(13 - ean.length) + ean;
        return ean.substr(0, 12) + this.get_barcode_check_digit(ean);
    }

    /**
     * Sanitizes a UPC-A prefix by padding it with chars zero.
     *
     * @param {String} upc
     * @returns {String}
     */
    sanitize_upc(upc) {
        return this.sanitize_ean(upc).substr(1, 12);
    }

    // Checks if barcode matches the pattern
    // Additionnaly retrieves the optional numerical content in barcode
    // Returns an object containing:
    // - value: the numerical value encoded in the barcode (0 if no value encoded)
    // - base_code: the barcode in which numerical content is replaced by 0's
    // - match: boolean
    match_pattern(barcode, pattern, encoding) {
        var match = {
            value: 0,
            base_code: barcode,
            match: false,
        };
        barcode = barcode.replace("\\", "\\\\").replace("{", '\{').replace("}", "\}").replace(".", "\.");

        var numerical_content = pattern.match(/[{][N]*[D]*[}]/); // look for numerical content in pattern
        var base_pattern = pattern;
        if(numerical_content){ // the pattern encodes a numerical content
            var num_start = numerical_content.index; // start index of numerical content
            var num_length = numerical_content[0].length; // length of numerical content
            var value_string = barcode.substr(num_start, num_length-2); // numerical content in barcode
            var whole_part_match = numerical_content[0].match("[{][N]*[D}]"); // looks for whole part of numerical content
            var decimal_part_match = numerical_content[0].match("[{N][D]*[}]"); // looks for decimal part
            var whole_part = value_string.substr(0, whole_part_match.index+whole_part_match[0].length-2); // retrieve whole part of numerical content in barcode
            var decimal_part = "0." + value_string.substr(decimal_part_match.index, decimal_part_match[0].length-1); // retrieve decimal part
            if (whole_part === ''){
                whole_part = '0';
            }
            match.value = parseInt(whole_part) + parseFloat(decimal_part);

            // replace numerical content by 0's in barcode and pattern
            match.base_code = barcode.substr(0, num_start);
            base_pattern = pattern.substr(0, num_start);
            for(var i=0;i<(num_length-2);i++) {
                match.base_code += "0";
                base_pattern += "0";
            }
            match.base_code += barcode.substr(num_start + num_length - 2, barcode.length - 1);
            base_pattern += pattern.substr(num_start + num_length, pattern.length - 1);

            match.base_code = match.base_code
                .replace("\\\\", "\\")
                .replace("\{", "{")
                .replace("\}","}")
                .replace("\.",".");

            var base_code = match.base_code.split('');
            if (encoding === 'ean13') {
                base_code[12] = '' + this.get_barcode_check_digit(match.base_code);
            } else if (encoding === 'ean8') {
                base_code[7]  = '' + this.get_barcode_check_digit(match.base_code);
            } else if (encoding === 'upca') {
                base_code[11] = '' + this.get_barcode_check_digit(match.base_code);
            }
            match.base_code = base_code.join('');
        }

        base_pattern = base_pattern.split('|')
            .map(part => part.startsWith('^') ? part : '^' + part)
            .join('|');
        match.match = match.base_code.match(base_pattern);

        return match;
    }

    /**
     * Attempts to interpret a barcode (string encoding a barcode Code-128)
     *
     * @param {string} barcode
     * @returns {Object} the returned object containing informations about the barcode:
     *      - code: the barcode
     *      - type: the type of the barcode (e.g. alias, unit product, weighted product...)
     *      - value: if the barcode encodes a numerical value, it will be put there
     *      - base_code: the barcode with all the encoding parts set to zero; the one put on the product in the backend
     */
    parse_barcode(barcode) {
        if (barcode.match(/^urn:/)) {
            return this.parseURI(barcode);
        }
        return this.parseBarcodeNomenclature(barcode);
    }

    parseBarcodeNomenclature(barcode) {
        const parsed_result = {
            encoding: '',
            type:'error',
            code:barcode,
            base_code: barcode,
            value: 0,
        };

        if (!this.nomenclature) {
            return parsed_result;
        }

        var rules = this.nomenclature.rules;
        for (var i = 0; i < rules.length; i++) {
            var rule = rules[i];
            var cur_barcode = barcode;

            if (    rule.encoding === 'ean13' &&
                    this.check_encoding(barcode,'upca') &&
                    this.nomenclature.upc_ean_conv in {'upc2ean':'','always':''} ){
                cur_barcode = '0' + cur_barcode;
            } else if (rule.encoding === 'upca' &&
                    this.check_encoding(barcode,'ean13') &&
                    barcode[0] === '0' &&
                    this.nomenclature.upc_ean_conv in {'ean2upc':'','always':''} ){
                cur_barcode = cur_barcode.substr(1,12);
            }

            if (!this.check_encoding(cur_barcode,rule.encoding)) {
                continue;
            }

            var match = this.match_pattern(cur_barcode, rules[i].pattern, rule.encoding);
            if (match.match) {
                if(rules[i].type === 'alias') {
                    barcode = rules[i].alias;
                    parsed_result.code = barcode;
                    parsed_result.type = 'alias';
                }
                else {
                    parsed_result.encoding  = rules[i].encoding;
                    parsed_result.type      = rules[i].type;
                    parsed_result.value     = match.value;
                    parsed_result.code      = cur_barcode;
                    if (rules[i].encoding === "ean13"){
                        parsed_result.base_code = this.sanitize_ean(match.base_code);
                    }
                    else{
                        parsed_result.base_code = match.base_code;
                    }
                    return parsed_result;
                }
            }
        }
        return parsed_result;
    }

    // URI methods
    /**
     * Parse an URI into an object with either the product and its lot/serial
     * number, either the package.
     * @param {String} barcode
     * @returns {Object}
     */
    parseURI(barcode) {
        const uriParts = barcode.split(":").map(v => v.trim());
        // URI should be formatted like that (number is the index once split):
        // 0: urn, 1: epc, 2: id/tag, 3: identifier, 4: data
        const identifier = uriParts[3];
        const data = uriParts[4].split(".");
        if (identifier === "lgtin" || identifier === "sgtin") {
            return this.convertURIGTINDataIntoProductAndTrackingNumber(barcode, data);
        } else if (identifier === "sgtin-96" || identifier === "sgtin-198") {
            // Same compute then SGTIN but we have to remove the filter.
            return this.convertURIGTINDataIntoProductAndTrackingNumber(barcode, data.slice(1));
        } else if (identifier === "sscc") {
            return this.convertURISSCCDataIntoPackage(barcode, data);
        } else if (identifier === "sscc-96") {
            // Same compute then SSCC but we have to remove the filter.
            return this.convertURISSCCDataIntoPackage(barcode, data.slice(1));
        }
        return barcode;
    }

    convertURIGTINDataIntoProductAndTrackingNumber(base_code, data) {
        const [gs1CompanyPrefix, itemRefAndIndicator, trackingNumber] = data;
        const indicator = itemRefAndIndicator[0];
        const itemRef = itemRefAndIndicator.slice(1);
        let productBarcode = indicator + gs1CompanyPrefix + itemRef;
        productBarcode += this.get_barcode_check_digit(productBarcode + "0");
        return [
            {
                base_code,
                code: productBarcode,
                string_value: productBarcode,
                type: "product",
                value: productBarcode,
            }, {
                base_code,
                code: trackingNumber,
                string_value: trackingNumber,
                type: "lot",
                value: trackingNumber,
            }
        ];
    }

    convertURISSCCDataIntoPackage(base_code, data) {
        const [gs1CompanyPrefix, serialReference] = data;
        const extension = serialReference[0];
        const serialRef = serialReference.slice(1);
        let sscc = extension + gs1CompanyPrefix + serialRef;
        sscc += this.get_barcode_check_digit(sscc + "0");
        return [{
            base_code,
            code: sscc,
            string_value: sscc,
            type: "package",
            value: sscc,
        }];
    }
}
