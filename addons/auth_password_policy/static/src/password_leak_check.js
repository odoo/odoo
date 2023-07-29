/** @odoo-module **/

export async function isPasswordLeaked(password) {
    let hash = (await sha1(password)).toUpperCase();
    let prefix = hash.slice(0, 5);

    let response = await fetch(`https://api.pwnedpasswords.com/range/${prefix}`, {
        headers: {'User-Agent': 'Odoo'},
        signal: AbortSignal.timeout(3000), // 3 seconds.
    });
    let hashList = await response.text();
    return hashList.includes(hash.slice(5));
}

async function sha1(message) {
    let msgUint8 = new TextEncoder().encode(message);
    let hashBuffer = await crypto.subtle.digest("SHA-1", msgUint8);
    let hashArray = Array.from(new Uint8Array(hashBuffer));
    // Convert bytes to hex string.
    return hashArray
        .map((b) => b.toString(16).padStart(2, "0"))
        .join("");
}
