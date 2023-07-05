/** @odoo-module **/

// Override the Session.session_reload function
// The wowl test infrastructure does set a correct odoo global value before each test
// while the session is built only once for all tests.
// So if a test does a session_reload, it will merge the odoo global of that test
// into the session, and will alter every subsequent test of the suite.
// Obviously, we don't want that, ever.
import { session as sessionInfo } from "@web/session";
const initialSessionInfo = Object.assign({}, sessionInfo);
import Session from "web.Session";
import { patch } from "@web/core/utils/patch";

patch(Session.prototype, "web.SessionTestPatch", {
    async session_reload() {
        for (const key in sessionInfo) {
            delete sessionInfo[key];
        }
        for (const key in initialSessionInfo) {
            sessionInfo[key] = initialSessionInfo[key];
        }
        return await this._super(...arguments);
    },
});
