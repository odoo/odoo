import { registry } from "@web/core/registry";
import { SCHEME_TEMPLATE, FIELD_TEMPLATE, PARTITION} from "./epc_codec_model";

// Private
// Utilities
const DECODING_FUNCTIONS = {
    'integer': decodeInteger,
    'partition_table': decodePartition,
};

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
    let read = value >> BigInt(bitLength - indexEnd);
    const mask = (1n << BigInt(length)) - 1n;
    read &= mask;
    return read;
}

// EPC encoding must have a multiple of 16 bits.
// c.f. [TDS  2.1], §15.1.1
function missingBits(bitLength, standardSize = 16) {
    const remainder = bitLength % standardSize;
    return remainder === 0 ? 0 : (standardSize - remainder);
}

function decodeField(encoding, model, fieldName) {
    const decodeFunction = DECODING_FUNCTIONS[encoding];
    if (decodeFunction) {
        return decodeFunction(model, fieldName);
    } else {
        throw new Error(`No decode function found for encoding: ${encoding}`);
    }
}

function getSplitUri(uri) {
    const uriHeader = uri.split(':');
    const uriBody = uriHeader.pop();
    return [uriHeader.join(':'), uriBody.split('.')];
}

// Decode Methods
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

//public
export async function decode(hexString){
    // Prepare values
    const hexValue = BigInt('0x' + hexString);
    const bitLength = getBitLength(hexValue);
    const headerRealBitCount = 8 - missingBits(bitLength, 8); // compensate for leftmost missing 0
    const header = readBits(hexValue, 0, headerRealBitCount, bitLength);

    //Find template
    const template = SCHEME_TEMPLATE[header];
    if(template == null || template.name !== 'SGTIN-96'){ // Only support SGTIN-96 actually
        return null;
    }

    // Create & initialize base scheme structure
    let model = {
        'hexValue': hexValue,
        'bitLength': bitLength,
        'partition': template.partition,
        'fields': {},
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
        previous_field = fieldEntries[i - 1][1];
        fieldInfo.offset = previous_field.offset + previous_field.bitSize;
        fieldInfo.value = decodeField(fieldInfo.encoding, model, fieldName);
    }

    // Construct URI
    const [uriHeader, uriBody] = getSplitUri(template.uri_pure_tag);
    for (let i = 0; i < fieldEntries.length; i++) {
        index = uriBody.indexOf(fieldEntries[i][1].uriPortion);
        if(index !== -1){
            uriBody[index] = fieldEntries[i][1].value;
        }
    }
    return uriHeader + ':' + uriBody.join('.');
}

export const EPCCodecService = {
    start() {
        return {decode}
    },
};
registry.category("services").add("epc_codec", EPCCodecService);
