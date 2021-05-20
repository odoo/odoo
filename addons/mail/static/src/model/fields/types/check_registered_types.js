/** @odoo-module **/

/**
 * @param {Object} param0
 * @param {Object} param0.env
 * @param {Map} param0.fieldTypeRegistry
 * @throws {Error} in case some registered types are not correctly defined
 */
export function checkRegisteredTypes({ env, fieldTypeRegistry }) {
    if (!(fieldTypeRegistry instanceof Map)) {
        throw new Error(`The field type registry should be a Map.`);
    }
    for (const [registeredTypeName, registeredType] of fieldTypeRegistry) {
        try {
            checkRegisteredType({ env, registeredType });
        } catch (error) {
            error.message = `Invalid registered type "${registeredTypeName}": ${error.message}`;
            throw error;
        }
    }
}

/**
 * @param {Object} param0
 * @param {Object} param0.env
 * @param {Map} param0.registeredType
 * @throws {Error} in case the registered type is not correctly defined
 */
function checkRegisteredType({ env, registeredType }) {
    if (!(registeredType instanceof Map)) {
        throw new Error(`should be a Map`);
    }
    for (const [key, value] of registeredType) {
        switch (key) {
            case 'nameOfAvailableProperties':
                if (!(value instanceof Set)) {
                    throw new Error(`"nameOfAvailableProperties" should be a Set`);
                }
                for (const availableProperty of value) {
                    if (!env.modelManager.fieldPropertyRegistry.get(availableProperty)) {
                        throw new Error(`Property "${availableProperty}" from "nameOfAvailableProperties" is not registerd. Maybe check for typos? Registered properties: ${[...env.modelManager.fieldPropertyRegistry.keys()].join(", ")}.`);
                    }
                }
                break;
            case 'nameOfRequiredProperties':
                if (!(value instanceof Set)) {
                    throw new Error(`"nameOfRequiredProperties" should be a Set`);
                }
                for (const requiredProperty of value) {
                    if (!env.modelManager.fieldPropertyRegistry.get(requiredProperty)) {
                        throw new Error(`Property "${requiredProperty}" from "nameOfRequiredProperties" is not registerd. Maybe check for typos? Registered properties: ${[...env.modelManager.fieldPropertyRegistry.keys()].join(", ")}.`);
                    }
                }
                break;
            default:
                throw new Error(`key "${key}" is not allowed. Maybe check for typos? Allowed keys: "nameOfAvailableProperties", "nameOfRequiredProperties".`);
        }
    }
}
