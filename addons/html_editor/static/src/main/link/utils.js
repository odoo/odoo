/* eslint-disable */

const tldWhitelist = [
    "com", "net", "org", "ac", "ad", "ae", "af", "ag", "ai", "al", "am", "an",
    "ao", "aq", "ar", "as", "at", "au", "aw", "ax", "az", "ba", "bb", "bd",
    "be", "bf", "bg", "bh", "bi", "bj", "bl", "bm", "bn", "bo", "br", "bq",
    "bs", "bt", "bv", "bw", "by", "bz", "ca", "cc", "cd", "cf", "cg", "ch",
    "ci", "ck", "cl", "cm", "cn", "co", "cr", "cs", "cu", "cv", "cw", "cx",
    "cy", "cz", "dd", "de", "dj", "dk", "dm", "do", "dz", "ec", "ee", "eg",
    "eh", "er", "es", "et", "eu", "fi", "fj", "fk", "fm", "fo", "fr", "ga",
    "gb", "gd", "ge", "gf", "gg", "gh", "gi", "gl", "gm", "gn", "gp", "gq",
    "gr", "gs", "gt", "gu", "gw", "gy", "hk", "hm", "hn", "hr", "ht", "hu",
    "id", "ie", "il", "im", "in", "io", "iq", "ir", "is", "it", "je", "jm",
    "jo", "jp", "ke", "kg", "kh", "ki", "km", "kn", "kp", "kr", "kw", "ky",
    "kz", "la", "lb", "lc", "li", "lk", "lr", "ls", "lt", "lu", "lv", "ly",
    "ma", "mc", "md", "me", "mf", "mg", "mh", "mk", "ml", "mm", "mn", "mo",
    "mp", "mq", "mr", "ms", "mt", "mu", "mv", "mw", "mx", "my", "mz", "na",
    "nc", "ne", "nf", "ng", "ni", "nl", "no", "np", "nr", "nu", "nz", "om",
    "pa", "pe", "pf", "pg", "ph", "pk", "pl", "pm", "pn", "pr", "ps", "pt",
    "pw", "py", "qa", "re", "ro", "rs", "ru", "rw", "sa", "sb", "sc", "sd",
    "se", "sg", "sh", "si", "sj", "sk", "sl", "sm", "sn", "so", "sr", "ss",
    "st", "su", "sv", "sx", "sy", "sz", "tc", "td", "tf", "tg", "th", "tj",
    "tk", "tl", "tm", "tn", "to", "tp", "tr", "tt", "tv", "tw", "tz", "ua",
    "ug", "uk", "um", "us", "uy", "uz", "va", "vc", "ve", "vg", "vi", "vn",
    "vu", "wf", "ws", "ye", "yt", "yu", "za", "zm", "zr", "zw", "co\\.uk"];

const urlRegexBase = `|(?:www.))[-a-zA-Z0-9@:%._\\+~#=]{2,256}\\.[a-zA-Z][a-zA-Z0-9]{1,62}|(?:[-a-zA-Z0-9@:%._\\+~#=]{2,256}\\.(?:${tldWhitelist.join(
    "|"
)})\\b))(?:(?:[/?#])[^\\s]*[^!.,})\\]'"\\s]|(?:[^!(){}.,[\\]'"\\s]+))?`;
const httpCapturedRegex = `(https?:\\/\\/)`;

export const URL_REGEX = new RegExp(`((?:(?:${httpCapturedRegex}${urlRegexBase})`, "i");
export const EMAIL_REGEX = /^(mailto:)?[\w-.]+@(?:[\w-]+\.)+[\w-]{2,4}$/i;
export const PHONE_REGEX = /^(tel:(?:\/\/)?)?\+?[\d\s.\-()/]{3,25}$/;

export function cleanZWChars(text) {
    return text.replace(/\u200B|\uFEFF/g, "");
}

/**
 * Returns a complete URL if text is a valid email address, http URL or telephone
 * number, null otherwise.
 * The optional link parameter is used to prevent protocol switching between
 * 'http' and 'https'.
 *
 * @param {String} text
 * @param {HTMLAnchorElement} [link]
 * @returns {String|null}
 */
export function deduceURLfromText(text, link) {
    const label = cleanZWChars(text).trim();
    // Check first for e-mail.
    let match = label.match(EMAIL_REGEX);
    if (match) {
        return match[1] ? match[0] : "mailto:" + match[0];
    }
    // Check for http link.
    match = label.match(URL_REGEX);
    if (match && match[0] === label) {
        const currentHttpProtocol = (link?.href.match(/^http(s)?:\/\//gi) || [])[0];
        if (match[2]) {
            return match[0];
        } else if (currentHttpProtocol) {
            // Avoid converting a http link to https.
            return currentHttpProtocol + match[0];
        } else {
            return "https://" + match[0];
        }
    }
    // Check for telephone url.
    match = label.match(PHONE_REGEX);
    if (match) {
        return (match[1] ? match[0] : "tel:" + match[0]).replace(/\s+/g, "");
    }
    return null;
}

