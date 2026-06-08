/**
 * custom type to represent a boolean formated as an int in url params
 */
export class BooleanInt {}
/**
 * Convert the value of a given option in a string compatible with URL parameters.
 *
 * @param value
 * @param {Object} optionConfig
 * @returns {string} The value of the option formatted for URL parameter
 */
const convertOptionValueToUrlParam = (value, optionConfig) => {
    const { type, reversed } = optionConfig;
    switch (type) {
        case Boolean: {
            let convertedValue = [true, "1", "true"].includes(value) ? "true" : "false";
            if (reversed) {
                convertedValue = convertedValue === "true" ? "false" : "true";
            }
            return convertedValue;
        }
        case BooleanInt: {
            let convertedValue = [true, "1", "true"].includes(value) ? "1" : "0";
            if (reversed) {
                convertedValue = convertedValue === "1" ? "0" : "1";
            }
            return convertedValue;
        }
        case Number:
            return value.toString();
    }
    console.warn(`Unsupported option type: ${type}, returning raw option value.`);
    return value.toString();
};

/**
 * parse a url parameter value into the correct type based on the option configuration.
 *
 * @param paramValue
 * @param {Object} optionConfig
 * @returns {Boolean|Number|string}The value of the option
 */
const parseParams = (paramValue, optionConfig) => {
    const { type, reversed } = optionConfig;
    switch (type) {
        case BooleanInt:
        case Boolean: {
            let value = ["1", "true"].includes(paramValue);
            if (reversed) {
                value = !value;
            }
            return value;
        }
        case Number:
            return parseInt(paramValue);
    }
    console.warn(`Unsupported option type: ${type}, returning raw param value.`);
    return paramValue;
};

/**
 * Encode a set of option values to URL parameters.
 *
 * @param  {Object} options
 * @param  {Object} optionsConfig
 * @param  {string} muteParam
 * @returns {string}
 */
export function encodeOptionsToParams(options, optionsConfig, useBoolean = false) {
    const URLParams = [];
    // Sort the options alphabetically to build predictable URLs.
    // This helps a lot during unit tests.
    for (const optionName of Object.keys(options).sort()) {
        const optionValue = options[optionName];
        const config = optionsConfig?.[optionName];
        if (config?.params?.length) {
            const paramName = config.params[0];
            const isDefaultValue = optionValue === config.default;
            if (!isDefaultValue) {
                let paramValue = convertOptionValueToUrlParam(optionValue, config);
                if (useBoolean && config.type === Boolean) {
                    paramValue = paramName ? "true" : "false";
                }
                URLParams.push(`${encodeURI(paramName)}=${encodeURI(paramValue)}`);
            }
        }

        if (config?.linkedParams?.length) {
            for (const paramName of config.linkedParams) {
                const isDefaultValue = optionValue === config.default;
                if (!isDefaultValue) {
                    let paramValue = convertOptionValueToUrlParam(optionValue, config);
                    if (useBoolean && config.type === Boolean) {
                        paramValue = paramName ? "true" : "false";
                    }
                    URLParams.push(`${encodeURI(paramName)}=${encodeURI(paramValue)}`);
                }
            }
        }
    }
    return URLParams.join("&");
}

/**
 * Return the value of an option based on the url.
 * Returns the default value if no parameter is found in the URL.
 *
 * @param {URL} url
 * @param {Object} optionConfig
 * @returns {string}
 */
function getOption(url, optionConfig) {
    let value = optionConfig.default;
    const urlParams = url.searchParams;
    if (optionConfig.params) {
        for (const param of optionConfig.params) {
            const paramValue = urlParams.get(param);
            if (paramValue) {
                value = parseParams(paramValue, optionConfig);
                break;
            }
        }
    }
    return value;
}

/**
 * Return the options for the given URL.
 *
 * @param {URL} url
 * @param {Object} optionsConfig
 * @returns {Object}
 */
export function getUrlOptions(url, optionsConfig) {
    const options = {};
    for (const [key, config] of Object.entries(optionsConfig)) {
        const optionValue = getOption(url, config);
        options[key] = optionValue;
    }
    return options;
}
