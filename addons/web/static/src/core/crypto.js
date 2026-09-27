export const CRYPTO_ALGO = "AES-GCM";

const decoder = new TextDecoder();
const encoder = new TextEncoder();

export class Crypto {
    constructor(secret) {
        this._cryptoKey = null;
        this._ready = window.crypto.subtle
            .importKey(
                "raw",
                new Uint8Array(secret.match(/../g).map((h) => parseInt(h, 16))).buffer,
                CRYPTO_ALGO,
                false,
                ["encrypt", "decrypt"]
            )
            .then((encryptedKey) => {
                this._cryptoKey = encryptedKey;
            });
    }

    async encrypt(value) {
        await this._ready;
        // The iv must never be reused with a given key.
        const iv = window.crypto.getRandomValues(new Uint8Array(12));
        const ciphertext = await window.crypto.subtle.encrypt(
            {
                name: CRYPTO_ALGO,
                iv,
                length: 64, // length of the counter in bits
            },
            this._cryptoKey,
            encoder.encode(JSON.stringify(value)) // encoded Data
        );
        return { ciphertext, iv };
    }

    async decrypt({ ciphertext, iv }) {
        await this._ready;
        const decrypted = await window.crypto.subtle.decrypt(
            {
                name: CRYPTO_ALGO,
                iv,
                length: 64,
            },
            this._cryptoKey,
            ciphertext
        );
        return JSON.parse(decoder.decode(decrypted));
    }
}
