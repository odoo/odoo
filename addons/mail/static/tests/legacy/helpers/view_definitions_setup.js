/** @odoo-module alias=@mail/../tests/helpers/view_definitions_setup default=false */

import { registry } from "@web/core/registry";

registry
    .category("bus.view.archs")
    .category("form")
    .add(
        "res.fake",
        `<form>
            <sheet/>
            <div class="oe_chatter">
                <field name="message_ids"/>
                <field name="message_follower_ids"/>
            </div>
        </form>`
    );
