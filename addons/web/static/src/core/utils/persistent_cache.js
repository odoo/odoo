import { Deferred } from "@web/core/utils/concurrency";
import { IndexedDB } from "@web/core/utils/indexed_db";
import { deepCopy } from "./objects";

const CRYPTO_ALGO = "AES-GCM";

class Crypto {
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
            new TextEncoder().encode(JSON.stringify(value)) // encoded Data
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
        return JSON.parse(new TextDecoder().decode(decrypted));
    }
}

class RamCache {
    constructor() {
        this.ram = {};
    }

    write(table, key, value) {
        if (!(table in this.ram)) {
            this.ram[table] = {};
        }
        this.ram[table][key] = value;
    }

    read(table, key) {
        return this.ram[table]?.[key];
    }

    delete(table, key) {
        delete this.ram[table]?.[key];
    }

    invalidate(tables = null) {
        if (tables) {
            tables = typeof tables === "string" ? [tables] : tables;
            for (const table of tables) {
                if (table in this.ram) {
                    this.ram[table] = {};
                }
            }
        } else {
            this.ram = {};
        }
    }
}

export class PersistentCache {
    constructor(name, version, secret) {
        this.crypto = new Crypto(secret);
        this.indexedDB = new IndexedDB(name, version + CRYPTO_ALGO);
        this.ramCache = new RamCache();
    }

    read(table, key, fallback, { onUpdate } = {}) {
        const ramValue = this.ramCache.read(table, key);
        if (ramValue && !onUpdate) {
            return ramValue.then((value) => deepCopy(value));
        }
        const def = new Deferred();
        const fromCache = new Deferred();
        let fromCacheValue;
        const prom = fallback()
            .then((result) => {
                def.resolve(deepCopy(result));
                this.ramCache.write(table, key, Promise.resolve(result));
                if (onUpdate && fromCacheValue && fromCacheValue !== JSON.stringify(result)) {
                    onUpdate(deepCopy(result));
                }
                this.crypto.encrypt(result).then((encryptedResult) => {
                    this.indexedDB.write(table, key, encryptedResult);
                });
                return result;
            })
            .catch(async (error) => {
                await fromCache;
                if (fromCacheValue) {
                    // def has already been fullfilled with the cached value
                    throw error;
                }
                this.ramCache.delete(table, key); // remove rejected prom from ram cache
                def.reject(error);
            });
        if (ramValue) {
            ramValue.then((value) => {
                def.resolve(deepCopy(value));
                fromCacheValue = JSON.stringify(value);
                fromCache.resolve();
            });
        } else {
            this.ramCache.write(table, key, prom);
            this.indexedDB.read(table, key).then(async (result) => {
                if (result) {
                    let decrypted;
                    try {
                        decrypted = await this.crypto.decrypt(result);
                    } catch {
                        fromCache.resolve();
                        // Do nothing ! The cryptoKey is probably different.
                        // The data will be updated with the new cryptoKey.
                        return;
                    }
                    def.resolve(deepCopy(decrypted));
                    this.ramCache.write(table, key, Promise.resolve(decrypted));
                    fromCacheValue = JSON.stringify(decrypted);
                }
                fromCache.resolve();
            });
        }
        return def;
    }

    invalidate(tables) {
        this.indexedDB.invalidate(tables);
        this.ramCache.invalidate(tables);
    }
}
