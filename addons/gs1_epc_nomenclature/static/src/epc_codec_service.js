import { registry } from "@web/core/registry";
import { SCHEME_TEMPLATE, FIELD_TEMPLATE, PARTITION} from "./epc_codec_model";

// Private
const DECODING_FUNCTIONS = {
    'blank': decodeBlank,
    'integer': decodeInteger,
    'partition_table': decodePartition,
    'string': decodeString,
};

const AI_FUNCTIONS = {
    '00' : getAi00,
    '01' : getAi01,
}

//  Technical Utilities
function getBitLength(num) {
    if (num === 0n) return 1;  // Special case for 0
    let bitLength = 0;
    while (num > 0n) {
        num >>= 1n;
        bitLength++;
    }
    return bitLength;
}

function readBits(value, index, length, bitLength = null) {
    if (index < 0 || length < 0) {
        throw new Error("Index and length must be non-negative");
    }
    if(bitLength === null){
        bitLength = getBitLength(value);
    }
    const indexEnd = index + length;
    if (indexEnd > bitLength) {
        throw new Error("Index range exceeds bit length of the value");
    }
    let read = value >> BigInt(bitLength - indexEnd); // Remove the rightmost unwanted part
    const mask = (1n << BigInt(length)) - 1n; // And Mask to extract the wanted part
    read &= mask;
    return read;
}

// EPC encoding must have a multiple of 16 bits.
// c.f. [TDS  2.1], §15.1.1
function missingBits(bitLength, standardSize = 16) {
    const remainder = bitLength % standardSize;
    return remainder === 0 ? 0 : (standardSize - remainder);
}

// Decode Methods
function decodeField(encoding, model, fieldName) {
    const decodeFunction = DECODING_FUNCTIONS[encoding];
    if (decodeFunction) {
        return decodeFunction(model, fieldName);
    } else {
        throw new Error(`No decode function found for encoding: ${encoding}`);
    }
}

function decodeBlank(model, fieldName){
    return null;
}

function decodeInteger(model, fieldName){
    const field = model.fields[fieldName];
    const value = readBits(model.hexValue, field.offset, field.bitSize, model.bitLength);
    res = value.toString();
    //Improve later
    if(field.digits){
        res = res.padStart(field.digits, '0');
    }
    return res;
}


function decodePartition(model, fieldName){
    const field = model.fields[fieldName];
    const partition = PARTITION[model.partition];
    if(partition === undefined){
        throw new Error(`No partition found for value: ${model.partition}`);
    }
    const value = readBits(model.hexValue, field.offset, field.bitSize, model.bitLength);
    const fieldEntries = Object.entries(model.fields);
    const fieldIndex = fieldEntries.findIndex(([name]) => name === fieldName);
    if (fieldIndex === -1 || fieldIndex + 2 >= fieldEntries.length) {
        throw new Error(`Field ${fieldName} or subsequent fields are not defined.`);
    }
    // Update the bitSize of the next two fields based on partition information
    const [nextFieldName1] = fieldEntries[fieldIndex + 1];
    const [nextFieldName2] = fieldEntries[fieldIndex + 2];
    model.fields[nextFieldName1].bitSize = partition[value].left_bit;
    model.fields[nextFieldName1].digits = partition[value].left_digit;
    model.fields[nextFieldName2].bitSize = partition[value].right_bit;
    model.fields[nextFieldName2].digits = partition[value].right_digit;

    return null;
}

function decodeString(model, fieldName){
    const field =  model.fields[fieldName];
    const value = readBits(model.hexValue, field.offset, field.bitSize, model.bitLength);
    const charLength = field.bitSize / 7;
    let charCodes = [];
    // loop read 7 bits at a time
    for (let i = 0; i < charLength; i++) {
        charCodes[i] = readBits(value, i * 7, 7, field.bitSize);
    }
    // parse to string & decode/unescape to UTF
    return decodeURIComponent(String.fromCharCode(...charCodes));
}

// 'Business' Utilities
function toPureUri(model){
    const fieldEntries = Object.entries(model.fields);
    const [uriHeader, uriBody] = getSplitUri(model.template.uri_pure_tag);
    for (let i = 0; i < fieldEntries.length; i++) {
        index = uriBody.indexOf(fieldEntries[i][1].uriPortion);
        if(index !== -1){
            uriBody[index] = fieldEntries[i][1].value;
        }
    }
    return uriHeader + ':' + uriBody.join('.');
}

function getSplitUri(uri) {
    const uriHeader = uri.split(':');
    const uriBody = uriHeader.pop();
    return [uriHeader.join(':'), uriBody.split('.')];
}

function toElementString(model){
    const aiDict = model.template.ai_list
    const identifiers = Object.entries(aiDict);

    for(identifier in identifiers){
        if(aiDict[identifier] === null){
            elementString += getAi(identifier, model);
        } else {
            elementString += ` (${identifier}) ${model.fields[aiDict[identifier]].value}`
        }
    }
    return elementString.trimStart();  // to capture: (?:\((?<key>\d{2,4})\)\s*(?<value>[^\(\)]+)?)\s*
}

function getAi(identifier, model){
    const aiFunction = AI_FUNCTIONS[identifier];
    if (aiFunction) {
        return aiFunction(model);
    } else {
        throw new Error(`No extrapolation function found for the GS1 Application Identifier (${identifier})`);
    }
}

function getAi00(model){
    const companyPrefix = model.fields['company_prefix'];
    const serialInteger = model.fields['serial_integer'];

    const extensionDigit = serialInteger.value.substr(0, 1);
    const serialRefRemainder = serialInteger.value.substr(1);
    const ssccToCheck = extensionDigit + companyPrefix.value + serialRefRemainder;
    const checkdigit = getGs1Checksum(ssccToCheck);
    return ' (00) ' + ssccToCheck + checkdigit;
}

function getAi01(model){
    // input length : sum of companyPrefix.digits and itemReference.digits is always 13 digits (preserving leading zeroes)
    // output: 14 digits
    const companyPrefix = model.fields['company_prefix'];
    const itemReference = model.fields['item_reference'];

    const indicator = itemReference.value.substr(0, 1);
    const itemRefRemainder = itemReference.value.substr(1);
    const gtinToCheck = indicator + companyPrefix.value + itemRefRemainder;
    const checkdigit = getGs1Checksum(gtinToCheck);
    return ' (01) ' + gtinToCheck + checkdigit;
}

function getGs1Checksum(data){
    // The GS1 specification defines the check digit calculation as follows (cf. [TDS 2.1] §7.3):
    // d14 = (10 - ((3(d1 + d3 + d5 + d7 + d9 + d11 + d13) + (d2 + d4 + d6 + d8 + d10 + d12)) mod 10) mod 10
    // However, it should be noted that here the index starts at 0 and not 1.
    // It is therefore necessary to multiply even numbers instead of odd numbers.

    // Note : same method is used for multiple data structures up to 17 digits (excluding check digits).
    // Cf. https://ref.gs1.org/standards/genspecs/ §7.9.1
    // data = data.padStart(17, '0'); //Maybe not optimal, cheat on i value of incoming for loop instead
    offset = 17 - data.length;
    let sum = 0;
    for(let i = 0; i < data.length; i++){
        const value = parseInt(data.charAt(i))
        if ((i + offset) % 2 == 0){
            sum += value * 3;
        }else{
            sum += value;
        }
    }
    return ((10 - (sum % 10)) % 10).toString();
}

//public
export async function decode(hexString){
    // Prepare values
    const hexValue = BigInt('0x' + hexString);
    const bitLength = getBitLength(hexValue);
    const headerRealBitCount = 8 - missingBits(bitLength, 8); // compensate for leftmost missing 0
    const header = readBits(hexValue, 0, headerRealBitCount, bitLength);

    //Find template
    const template = SCHEME_TEMPLATE[header];
    if(template == null || template.name !== 'SGTIN-96'){ // FIXME: Only support SGTIN-96 actually
        return null;
    }

    // Create & initialize base scheme structure
    let model = {
        'hexValue': hexValue,
        'bitLength': bitLength,
        'partition': template.partition,
        'fields': {},
        'template': template,
    }
    for (let i = 0; i < template.fields_template.length; i++) {
        const fieldName = template.fields_template[i];
        const FieldTemplate = FIELD_TEMPLATE[fieldName];
        const fieldBitCount = template.fields_bit_count[i];

        model.fields[fieldName] = {
            'encoding': FieldTemplate.encoding,
            'bitSize': i === 0 ? headerRealBitCount : fieldBitCount,
            'uriPortion': FieldTemplate.uri_portion,
            'offset': i === 0 ? 0 : null,
            'value': i === 0 ? header.toString() : null,
        };
    }

    // Effectively process fields
    const fieldEntries = Object.entries(model.fields);
    for (let i = 1; i < fieldEntries.length; i++) {
        let [fieldName, fieldInfo] = fieldEntries[i];
        previousField = fieldEntries[i - 1][1];
        fieldInfo.offset = previousField.offset + previousField.bitSize;
        fieldInfo.value = decodeField(fieldInfo.encoding, model, fieldName);
    }


    // return GS1 AI(s) as String
    if(template.element_string_template != null){
        return toElementString(model);
    }
    return toPureUri(model); // for GID-96, USDOD-96 and ADI-var. Cf. [TDT 2.0] Figure 1-1
}

export const EPCCodecService = {
    start() {
        return {decode}
    },
};
registry.category("services").add("epc_codec", EPCCodecService);
