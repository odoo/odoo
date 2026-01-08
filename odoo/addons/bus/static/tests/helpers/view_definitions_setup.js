/** @odoo-module **/

import { registry } from "@web/core/registry";

const viewArchsRegistry = registry.category("bus.view.archs");
const activityArchsRegistry = viewArchsRegistry.category("activity");
const formArchsRegistry = viewArchsRegistry.category("form");
const kanbanArchsRegistry = viewArchsRegistry.category("kanban");
const listArchsRegistry = viewArchsRegistry.category("list");
const searchArchsRegistry = viewArchsRegistry.category("search");

activityArchsRegistry.add("default", "<activity><templates></templates></activity>");
formArchsRegistry.add("default", "<form/>");
kanbanArchsRegistry.add("default", "<kanban><templates></templates>");
listArchsRegistry.add("default", "<tree/>");
searchArchsRegistry.add("default", "<search/>");

formArchsRegistry.add(
    "res.partner",
    `<form>
        <sheet>
            <field name="name"/>
        </sheet>
        <div class="oe_chatter">
            <field name="activity_ids"/>
            <field name="message_follower_ids"/>
            <field name="message_ids"/>
        </div>
    </form>`
);
