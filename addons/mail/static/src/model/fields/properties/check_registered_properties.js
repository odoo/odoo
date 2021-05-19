/** @odoo-module **/

/**
 * @param {Object} param0
 * @param {Map} param0.fieldPropertyRegistry
 * @throws {Error} in case some registered properties are not correctly defined
 */
export function checkRegisteredProperties({ fieldPropertyRegistry }) {
    if (!(fieldPropertyRegistry instanceof Map)) {
        throw new Error(`The field property registry should be a Map.`);
    }
    for (const [registeredPropertyName, registeredProperty] of fieldPropertyRegistry) {
        try {
            checkRegisteredProperty({ registeredProperty });
        } catch (error) {
            error.message = `Invalid registered property "${registeredPropertyName}": ${error.message}`;
            throw error;
        }
    }
}

/**
 * @param {Map} registeredProperty
 * @throws {Error} in case the registered property is not correctly defined
 */
function checkRegisteredProperty({ registeredProperty }) {
    if (!(registeredProperty instanceof Map)) {
        throw new Error(`should be a Map`);
    }
    for (const [key, value] of registeredProperty) {
        switch (key) {
            case 'excludedProperties':
                if (!(value instanceof Set)) {
                    throw new Error(`"excludedProperties" should be a Set`);
                }
                break;
            case 'isInstanceMethodName':
                if (typeof value !== "boolean") {
                    throw new Error(`"isInstanceMethodName" should be a boolean`);
                }
                break;
            case 'isModelName':
                if (typeof value !== "boolean") {
                    throw new Error(`"isModelName" should be a boolean`);
                }
                break;
            case 'isString':
                if (typeof value !== "boolean") {
                    throw new Error(`"isString" should be a boolean`);
                }
                break;
            case 'requiredProperties':
                if (!(value instanceof Set)) {
                    throw new Error(`"requiredProperties" should be a Set`);
                }
                break;
            default:
                throw new Error(`key "${key}" is not allowed. Maybe check for typos? Allowed keys: "excludedProperties", "isInstanceMethodName", "isModelName", "isString", "requiredProperties".`);
        }
    }
}
