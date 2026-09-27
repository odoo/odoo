/** @odoo-module */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const {
    Math: { random: $random, floor: $floor },
    TextEncoder,
} = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/** @type {SubtleCrypto["decrypt"]} */
function decrypt(algorithm, key, data) {
    return Promise.resolve($encode(data.replace("encrypted data:", "")));
}

/** @type {SubtleCrypto["encrypt"]} */
function encrypt(algorithm, key, data) {
    return Promise.resolve(`encrypted data:${$decode(data)}`);
}

/** @type {Crypto["getRandomValues"]} */
function getRandomValues(array) {
    for (let i = 0; i < array.length; i++) {
        array[i] = $floor($random() * 256);
    }
    return array;
}

/** @type {SubtleCrypto["importKey"]} */
function importKey(format, keyData, algorithm, extractable, keyUsages) {
    if (arguments.length < 5) {
        throw new TypeError(
            `Failed to execute 'importKey' on 'SubtleCrypto': 5 arguments required, but only ${arguments.length} present.`
        );
    }
    if (!keyData || keyData.length === 0) {
        throw new TypeError(
            `Failed to execute 'importKey' on 'SubtleCrypto': The provided value cannot be converted to a sequence.`
        );
    }
    const key = Symbol([algorithm, String(extractable), "secret", ...keyUsages].join("/"));
    return Promise.resolve(key);
}

function randomUUID() {
    return [4, 2, 2, 2, 6]
        .map((length) => getRandomValues(new Uint8Array(length)).toHex())
        .join("-");
}

const $encode = TextEncoder.prototype.encode.bind(new TextEncoder());
const $decode = TextDecoder.prototype.decode.bind(new TextDecoder("utf-8"));

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export const mockCrypto = {
    getRandomValues,
    randomUUID,
    subtle: {
        decrypt,
        encrypt,
        importKey,
    },
};
