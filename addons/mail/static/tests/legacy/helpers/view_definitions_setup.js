/** @odoo-module alias=@mail/../tests/helpers/view_definitions_setup default=false */

import { registry } from "@web/core/registry";

registry
    .category("bus.view.archs")
    .category("form")
    .add(
        "res.fake",
        `<form>
            <sheet/>
            <chatter/>
        </form>`
    );
