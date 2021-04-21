/** @odoo-module **/

import { Registry } from "../core/registry";

// -----------------------------------------------------------------------------
// Main Components
// -----------------------------------------------------------------------------

// Components registered in this registry will be rendered inside the root node
// of the webclient.
export const mainComponentRegistry = (odoo.mainComponentRegistry = new Registry());
