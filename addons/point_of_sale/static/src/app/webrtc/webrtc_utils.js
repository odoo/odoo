export function identifierToString(identifier) {
    if (identifier.device_b === null) {
        identifier.device_b = odoo.login_number;
    }

    const values = Object.values(identifier);
    const sortedValues = values.sort((a, b) => {
        const aInt = parseInt(a, 10);
        const bInt = parseInt(b, 10);
        return aInt < bInt ? -1 : aInt > bInt ? 1 : 0;
    });

    return sortedValues.join("-");
}
