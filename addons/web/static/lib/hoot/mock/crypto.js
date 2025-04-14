/** @odoo-module */

export const mockCrypto = {
    subtle: {
        importKey: (_format, keyData, _algorithm, _extractable, _keyUsages) => {
            if (!keyData || keyData.length === 0) {
                throw Error(`KeyData is mandatory`);
            }
            return Promise.resolve("I'm a key");
        },
        encrypt: (_algorithm, _key, data) =>
            Promise.resolve(`encrypted data:${new TextDecoder().decode(data)}`),
        decrypt: (_algorithm, _key, data) =>
            Promise.resolve(new TextEncoder().encode(data.replace("encrypted data:", ""))),
    },
    getRandomValues: (typedArray) => {
        typedArray.forEach((_element, index) => {
            typedArray[index] = Math.round(Math.random() * 100);
        });
        return typedArray;
    },
};
