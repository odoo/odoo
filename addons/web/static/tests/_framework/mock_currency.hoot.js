// ! WARNING: this module cannot depend on modules not ending with ".hoot" (except libs) !

import { onServerStateChange } from "./mock_server_state.hoot";

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @param {import("./mock_server_state.hoot").ServerState} serverState
 */
const makeCurrencies = ({ currencies }) =>
    Object.fromEntries(
        currencies.map((currency) => [currency.id, { digits: [69, 2], ...currency }])
    );

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * @param {string} name
 * @param {OdooModule} module
 */
export function mockCurrencyFactory(name, { fn }) {
    return (requireModule, ...args) => {
        const currencyModule = fn(requireModule, ...args);

        onServerStateChange(currencyModule.currencies, makeCurrencies);

        return currencyModule;
    };
}
