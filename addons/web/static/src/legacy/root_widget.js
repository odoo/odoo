/** @odoo-module alias=root.widget **/
/**
 * This module exists so that web_tour can use it as the parent of the
 * TourManager so it can get access to _trigger_up.
 */
// need to wait for owl.Component.env to be set by web.legacySetup
import "web.legacySetup";
import { ComponentAdapter } from "web.OwlCompatibility";
// for its method _trigger_up. We can't use a standalone adapter because it
// attempt to call env.isDebug which is not defined in the tests when this
// module is loaded.
export default new ComponentAdapter({ Component: owl.Component }, owl.Component.env);
