/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { Patch } from "@web/core/utils/patch";

// Ensure 'delivery_active' is loaded with pos.session
// In Odoo 16+ this is often done via python 'models' loading definition
// But let's check if we need to extend the loader arguments.
// Actually, usually fields on pos.session are NOT loaded automatically unless specified.
// However, 'pos.session' is loaded with *read* permissions.
// We can assume we might need to rely on the backend call if it's missing, or patch the load_server_data.

// Ideally, we add it to the configuration of loaded models.
// But as a robust fallback, we don't strictly "Crash" if it's missing, relying on the toggle to set state.
// BUT, to show correct initial state, we need it. 

// Odoo 19 might use a different loader mechanism. 
// A safer bet is to extend the python model to include it in `_loader_params_pos_session`.
