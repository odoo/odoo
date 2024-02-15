// ! WARNING: this module cannot depend on modules not ending with ".hoot" (except libs) !

import { onServerStateChange } from "./mock_server_state.hoot";

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * @param {string} name
 * @param {OdooModule} module
 */
export function mockUserFactory(name, { fn }) {
    return (requireModule, ...args) => {
        const { session } = requireModule("@web/session");
        const userModule = fn(requireModule, ...args);

        onServerStateChange(userModule.user, () => userModule._makeUser(session));

        return userModule;
    };
}
