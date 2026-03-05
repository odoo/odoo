/**
 * @typedef {[high: number, low: number]} Int64Tuple
 */

/**
 * @param {Int64Tuple} a
 * @param {Int64Tuple} b
 */
const add = (a, b) => {
    const rl = a[1] + b[1];
    a[0] = (a[0] + b[0] + ((rl / 2) >>> 31)) >>> 0;
    a[1] = rl >>> 0;
};

/**
 * @param {Uint8Array} a
 * @param {number} offset
 */
const getInt = (a, offset) =>
    (a[offset + 3] << 24) | (a[offset + 2] << 16) | (a[offset + 1] << 8) | a[offset];

/**
 * @param {Int64Tuple} v0
 * @param {Int64Tuple} v1
 * @param {Int64Tuple} v2
 * @param {Int64Tuple} v3
 */
const sipRound = (v0, v1, v2, v3) => {
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
};

/**
 * @param {Int64Tuple} a
 * @param {number} n
 */
const unsignedLeftShift = (a, n) => {
    [a[0], a[1]] = [(a[0] << n) | (a[1] >>> (32 - n)), (a[1] << n) | (a[0] >>> (32 - n))];
};

/**
 * @param {Int64Tuple} a
 */
const unsignedLeftShift32 = (a) => {
    [a[1], a[0]] = [a[0], a[1]];
};

/**
 * @param {Int64Tuple} a
 * @param {Int64Tuple} b
 */
const xor = (a, b) => {
    a[0] ^= b[0];
    a[0] >>>= 0;
    a[1] ^= b[1];
    a[1] >>>= 0;
};

// Magic numbers dictated by the SipHash algorithm
const N_0 = [0x736f6d65, 0x70736575];
const N_1 = [0x646f7261, 0x6e646f6d];
const N_2 = [0x6c796765, 0x6e657261];
const N_3 = [0x74656462, 0x79746573];

const N_255 = [0, 255];

const encoder = new TextEncoder("utf-8");

/**
 * Implementation of the SipHash 2-4 algorithm
 * @see https://www.aumasson.jp/siphash/siphash.pdf
 *
 * @param {string} key
 * @param {string} data
 */
export function siphash(key, data) {
    if (typeof key === "string") {
        const u8Str = encoder.encode(key);
        if (u8Str.length !== 16) {
            throw new Error("Key length must be exactly 16 bytes or characters");
        }
        key = new Uint32Array(4);
        key[0] = getInt(u8Str, 0);
        key[1] = getInt(u8Str, 4);
        key[2] = getInt(u8Str, 8);
        key[3] = getInt(u8Str, 12);
    }
    if (typeof data === "string") {
        data = encoder.encode(data);
    }

    const v0 = [key[1] >>> 0, key[0] >>> 0];
    const v1 = [key[3] >>> 0, key[2] >>> 0];
    const v2 = [...v0];
    const v3 = [...v1];

    xor(v0, N_0);
    xor(v1, N_1);
    xor(v2, N_2);
    xor(v3, N_3);

    const dataLength = data.length;
    const dataLengthMin7 = dataLength - 7;
    let msgIdx = 0;
    while (msgIdx < dataLengthMin7) {
        const msgInt = [getInt(data, msgIdx + 4), getInt(data, msgIdx)];
        xor(v3, msgInt);
        sipRound(v0, v1, v2, v3);
        sipRound(v0, v1, v2, v3);
        xor(v0, msgInt);
        msgIdx += 8;
    }

    const buffer = new Uint8Array(8);
    buffer[7] = dataLength;

    let idxCounter = 0;
    while (msgIdx < dataLength) {
        buffer[idxCounter++] = data[msgIdx++];
    }
    while (idxCounter < 7) {
        buffer[idxCounter++] = 0;
    }

    const msgIntLast = [
        (buffer[7] << 24) | (buffer[6] << 16) | (buffer[5] << 8) | buffer[4],
        (buffer[3] << 24) | (buffer[2] << 16) | (buffer[1] << 8) | buffer[0],
    ];
    xor(v3, msgIntLast);

    sipRound(v0, v1, v2, v3);
    sipRound(v0, v1, v2, v3);

    xor(v0, msgIntLast);
    xor(v2, N_255);

    sipRound(v0, v1, v2, v3);
    sipRound(v0, v1, v2, v3);
    sipRound(v0, v1, v2, v3);
    sipRound(v0, v1, v2, v3);

    xor(v0, v1);
    xor(v0, v2);
    xor(v0, v3);

    return (v0[0].toString(16) + v0[1].toString(16)).padStart(16, "0");
}
