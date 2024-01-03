/** @odoo-module **/

import { defineModels, webModels } from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";
import { BusBus } from "./mock_server/mock_models/bus_bus";
import { IrWebSocket } from "./mock_server/mock_models/ir_websocket";

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export function defineBusModels() {
    return defineModels({ ...webModels, ...busModels });
}

export const busModels = { BusBus, IrWebSocket };

//-----------------------------------------------------------------------------
// Setup
//-----------------------------------------------------------------------------

const viewsRegistry = registry.category("bus.view.archs");
viewsRegistry.category("activity").add(
    "default",
    /* xml */ `
        <activity><templates /></activity>
    `
);
viewsRegistry.category("form").add("default", /* xml */ `<form />`);
viewsRegistry.category("kanban").add("default", /* xml */ `<kanban><templates /></kanban>`);
viewsRegistry.category("list").add("default", /* xml */ `<tree />`);
viewsRegistry.category("search").add("default", /* xml */ `<search />`);

viewsRegistry.category("form").add(
    "res.partner",
    /* xml */ `
    <form>
        <sheet>
            <field name="name" />
        </sheet>
        <div class="oe_chatter">
            <field name="activity_ids" />
            <field name="message_follower_ids" />
            <field name="message_ids" />
        </div>
    </form>`
);
