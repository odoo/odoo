/** @odoo-module alias=@bus/../tests/helpers/view_definitions_setup default=false */

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
listArchsRegistry.add("default", "<list/>");
searchArchsRegistry.add("default", "<search/>");

formArchsRegistry.add(
    "res.partner",
    `<form>
        <sheet>
            <field name="name"/>
        </sheet>
        <chatter/>
    </form>`
);
