/**
 * Convert the string from a data-behavior-props attribute to an usable object.
 *
 * @param {String} dataBehaviorPropsAttribute utf-8 encoded JSON string
 * @returns {Object} object containing props for a Behavior to store in the
 *                   html_field value of a field
 */
export function decodeDataBehaviorProps(dataBehaviorPropsAttribute) {
    if (!dataBehaviorPropsAttribute) {
        return undefined;
    }
    return JSON.parse(decodeURIComponent(dataBehaviorPropsAttribute));
}

/**
 * Return any existing propName node owned by the Behavior related to `anchor`.
 * Filter out propName nodes owned by children Behavior.
 *
 * @param {string} propName name of the htmlProp
 * @param {Element} anchor node to search for propName children
 * @returns {Element} last matching node (there should be only one, but it's
 *           always the last one that is taken as the effective prop)
 */
export function getPropNameNode(propName, anchor) {
    const propNodes = anchor.querySelectorAll(`[data-prop-name="${propName}"]`);
    for (let i = propNodes.length - 1; i >= 0; i--) {
        const closest = propNodes[i].closest(".o_knowledge_behavior_anchor");
        if (closest === anchor) {
            return propNodes[i];
        }
    }
}

/**
 * Generate a unique identifier (64 bits) in hexadecimal.
 *
 * @returns {string}
 */
export function uuid() {
    const array = new Uint8Array(8);
    window.crypto.getRandomValues(array);
    // Uint8Array to hex
    return [...array].map((b) => b.toString(16).padStart(2, "0")).join("");
}
