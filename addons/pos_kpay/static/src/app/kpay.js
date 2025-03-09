/* global pmlib */
export class KpayTerminal {
    constructor(settings) {
        this.settings = settings;
    }

    async sign(ignore_error = false) {
        try {
            const resultRaw = await fetch(`${this.settings.endpoint}/v1/pos/sign`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    timestamp: Date.now().toString(),
                    nonceStr: this._generateNonceStr(),
                },
                body: JSON.stringify({
                    appId: this.settings.appId,
                    appSecret: this.settings.appSecret,
                }),
            });
            const result = await resultRaw.json();
            if (result.code !== 10000) {
                throw new Error(result.message);
            }
            this.privateKey = result.data.appPrivateKey;
            if (!this.privateKey.startsWith("-----BEGIN PRIVATE KEY-----")) {
                this.privateKey = `-----BEGIN PRIVATE KEY-----\n${this.privateKey}\n-----END PRIVATE KEY-----`;
            }
            return result.data;
        } catch (err) {
            if (!ignore_error) {
                throw err;
            }
        }
    }

    async sales(payload) {
        return this._actionAsync("sales", payload).then((result) => result.json());
    }

    async cancel(payload) {
        return this._actionAsync("sales/cancel", payload).then((result) => result.json());
    }

    async close(payload) {
        return this._actionAsync("sales/close", payload).then((result) => result.json());
    }

    async _actionAsync(action, payload, method = "POST") {
        const endpoint = `/v2/pos/${action}`;
        const timestamp = Date.now().toString();
        const nonceStr = this._generateNonceStr();
        const signaturePayload = [method, endpoint, timestamp, nonceStr, JSON.stringify(payload)];
        return fetch(`${this.settings.endpoint}/v2/pos/${action}`, {
            method,
            headers: {
                "Content-Type": "application/json",
                appId: this.settings.appId,
                signature: this._generateSignature(signaturePayload),
                timestamp,
                nonceStr,
            },
            body: JSON.stringify(payload),
        });
    }

    _generateSignature(payload) {
        const signatureText = payload.join("\n") + "\n";
        const sha256withrsa = new pmlib.rs.KJUR.crypto.Signature({ alg: "SHA256withRSA" });
        sha256withrsa.init(this.privateKey);
        sha256withrsa.updateString(signatureText);
        return pmlib.rs.hextob64(sha256withrsa.sign());
    }

    _generateNonceStr() {
        return Array(32)
            .fill(0)
            .map(() => {
                const chars = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ";
                return chars.charAt(Math.floor(Math.random() * chars.length));
            })
            .join("");
    }
}

export class KpaySettings {
    constructor() {
        this.endpoint = "";
        this.appId = "";
        this.appSecret = "";
    }
}

export const PAYMENT_METHODS_MAPPING = {
    1: "Visa",
    2: "Mastercard",
    3: "中國銀聯",
    4: "微信",
    5: "支付寶",
    6: "American Express",
    7: "Diners Club",
    8: "JCB",
    9: "銀聯雲閃付",
    11: "八達通",
    12: "Payme",
};
