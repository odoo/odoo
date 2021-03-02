/** @odoo-module **/

import { Registry } from "../core/registry";
import { LoadingIndicator } from "./loading_indicator/loading_indicator";

// -----------------------------------------------------------------------------
// Main Components
// -----------------------------------------------------------------------------

// Components registered in this registry will be rendered inside the root node
// of the webclient.
export const mainComponentRegistry = odoo.mainComponentRegistry = new Registry();
mainComponentRegistry.add("LoadingIndicator", LoadingIndicator);
