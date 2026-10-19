/**
 * SipHash 2-4 implementation in JavaScript
 *
 * This lib is required to generate specific links to WebLate translations.
 *
 * For more details:
 * @see https://www.aumasson.jp/siphash/siphash.pdf
 */

/**
 * @typedef {Uint32Array<[high: Uint32, low: Uint32]>} Uint64Tuple
 * @typedef {number} Uint32
 */

/**
 * @param {Uint64Tuple} a
 * @param {Uint64Tuple} b
 */
function add(a, b) {
    a[0] = a[0] + b[0] + (((a[1] + b[1]) / 2) >>> 31);
    a[1] += b[1];
}

/**
 * @param {Uint8Array} a
 * @param {Uint32} offset
 * @returns {Uint32}
 */
function getUint32(a, offset) {
    return (a[offset + 3] << 24) | (a[offset + 2] << 16) | (a[offset + 1] << 8) | a[offset];
}

/**
 * @param {Uint64Tuple} v0
 * @param {Uint64Tuple} v1
 * @param {Uint64Tuple} v2
 * @param {Uint64Tuple} v3
 */
function sipRound(v0, v1, v2, v3) {
    add(v0, v1);
    add(v2, v3);

    unsignedLeftShift(v1, 13);
    unsignedLeftShift(v3, 16);

    xor(v1, v0);
    xor(v3, v2);

    unsignedLeftShift32(v0);

    add(v2, v1);
    add(v0, v3);

    unsignedLeftShift(v1, 17);
    unsignedLeftShift(v3, 21);

    xor(v1, v2);
    xor(v3, v0);

    unsignedLeftShift32(v2);
}

/**
 * @param {Uint64Tuple} a
 * @param {Uint32} n
 */
function unsignedLeftShift(a, n) {
    [a[0], a[1]] = [(a[0] << n) | (a[1] >>> (32 - n)), (a[1] << n) | (a[0] >>> (32 - n))];
}

/**
 * @param {Uint64Tuple} a
 */
function unsignedLeftShift32(a) {
    [a[1], a[0]] = [a[0], a[1]];
}

/**
 * @param {Uint64Tuple} a
 * @param {Uint64Tuple} b
 */
function xor(a, b) {
    a[0] ^= b[0];
    a[0] >>>= 0;
    a[1] ^= b[1];
    a[1] >>>= 0;
}

// Magic numbers dictated by the SipHash algorithm
/** @type {Uint64Tuple} */
const N_0 = new Uint32Array([0x736f6d65, 0x70736575]);
/** @type {Uint64Tuple} */
const N_1 = new Uint32Array([0x646f7261, 0x6e646f6d]);
/** @type {Uint64Tuple} */
const N_2 = new Uint32Array([0x6c796765, 0x6e657261]);
/** @type {Uint64Tuple} */
const N_3 = new Uint32Array([0x74656462, 0x79746573]);
/** @type {Uint64Tuple} */
const N_255 = new Uint32Array([0, 255]);

const encoder = new TextEncoder();

/**
 * Main entry point: takes a {@link key}, some {@link data} and returns a hash (string).
 *
 * @param {string} key
 * @param {string} data
 */
export function siphash(key, data) {
    const u8Key = encoder.encode(key);
    if (u8Key.length !== 16) {
        throw new Error("SipHash error: 'key' length must be exactly 16 bytes");
    }

    /** @type {Uint64Tuple} */
    const v0 = new Uint32Array(2);
    v0[0] = getUint32(u8Key, 4);
    v0[1] = getUint32(u8Key, 0);

    /** @type {Uint64Tuple} */
    const v1 = new Uint32Array(2);
    v1[0] = getUint32(u8Key, 12);
    v1[1] = getUint32(u8Key, 8);

    /** @type {Uint64Tuple} */
    const v2 = new Uint32Array(v0);
    /** @type {Uint64Tuple} */
    const v3 = new Uint32Array(v1);

    xor(v0, N_0);
    xor(v1, N_1);
    xor(v2, N_2);
    xor(v3, N_3);

    const u8Data = encoder.encode(data);

    const dataLength = u8Data.length;
    const dataLengthMin7 = dataLength - 7;
    /** @type {Uint64Tuple} */
    const msgInt = new Uint32Array(2);
    let msgIdx = 0;
    for (; msgIdx < dataLengthMin7; msgIdx += 8) {
        msgInt[0] = getUint32(u8Data, msgIdx + 4);
        msgInt[1] = getUint32(u8Data, msgIdx);
        xor(v3, msgInt);
        sipRound(v0, v1, v2, v3);
        sipRound(v0, v1, v2, v3);
        xor(v0, msgInt);
    }

    const buffer = new Uint8Array(8);
    buffer[7] = dataLength;

    let idxCounter = 0;
    while (msgIdx < dataLength) {
        buffer[idxCounter++] = u8Data[msgIdx++];
    }

    msgInt[0] = (buffer[7] << 24) | (buffer[6] << 16) | (buffer[5] << 8) | buffer[4];
    msgInt[1] = (buffer[3] << 24) | (buffer[2] << 16) | (buffer[1] << 8) | buffer[0];

    xor(v3, msgInt);

    sipRound(v0, v1, v2, v3);
    sipRound(v0, v1, v2, v3);

    xor(v0, msgInt);
    xor(v2, N_255);

    sipRound(v0, v1, v2, v3);
    sipRound(v0, v1, v2, v3);
    sipRound(v0, v1, v2, v3);
    sipRound(v0, v1, v2, v3);

    xor(v0, v1);
    xor(v0, v2);
    xor(v0, v3);

    return v0[0].toString(16).padStart(8, "0") + v0[1].toString(16).padStart(8, "0");
}
