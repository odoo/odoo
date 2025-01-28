import {
    startInteractions,
    setupInteractionWhiteList,
} from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
import { hover, leave } from "@odoo/hoot-dom";

import { switchToEditMode } from "../../helpers";

setupInteractionWhiteList("website.hoverable_dropdown");

describe.current.tags("interaction_dev");

test.tags("desktop")("[EDIT] onMouseLeave doesn't work in edit mode", async () => {
    const { core } = await startInteractions(`
        <header class="o_hoverable_dropdown" style="display: flex; height: 50px; background-color: #CCFFCC;">
            <div class="dropdown" style="margin: auto;">
                <a class="dropdown-toggle">Dropdown</a>
                <div class="dropdown-menu">
                    <a href="#" style="display: block;">A</a>
                    <a href="#" style="display: block;">B</a>
                    <a href="#" style="display: block;">C</a>
                </div>
            </div>
        </header>
    `, { waitForStart: true, editMode: true });
    await switchToEditMode(core);
    expect(".dropdown-toggle").not.toHaveClass("show");
    expect(".dropdown-menu > a").not.toBeVisible();
    await hover(".dropdown");
    expect(".dropdown-toggle").toHaveClass("show");
    expect(".dropdown-menu > a").toBeVisible();
    await leave(".dropdown");
    expect(".dropdown-toggle").toHaveClass("show");
    expect(".dropdown-menu > a").toBeVisible();
});

test.tags("desktop")("[EDIT] onMouseEnter doesn't work in edit mode if another dropdown is opened", async () => {
    const { core } = await startInteractions(`
        <header class="o_hoverable_dropdown" style="display: flex; height: 50px; background-color: #CCFFCC;">
            <div id="D1" class="dropdown" style="margin: auto;">
                <a class="dropdown-toggle">Dropdown 1</a>
                <div class="dropdown-menu">
                    <a href="#" style="display: block;">A1</a>
                    <a href="#" style="display: block;">B1</a>
                    <a href="#" style="display: block;">C1</a>
                </div>
            </div>
            <div id="D2" class="dropdown" style="margin: auto;">
                <a class="dropdown-toggle">Dropdown 2</a>
                <div class="dropdown-menu">
                    <a href="#" style="display: block;">A2</a>
                    <a href="#" style="display: block;">B2</a>
                    <a href="#" style="display: block;">C2</a>
                </div>
            </div>
        </header>
    `, { waitForStart: true, editMode: true });
    await switchToEditMode(core);
    expect(".dropdown-toggle").not.toHaveClass("show");
    expect(".dropdown-menu > a").not.toBeVisible();
    await hover("#D1.dropdown");
    expect("#D1 > .dropdown-toggle").toHaveClass("show");
    expect("#D1 > .dropdown-menu > a").toBeVisible();
    expect("#D2 > .dropdown-toggle").not.toHaveClass("show");
    expect("#D2 > .dropdown-menu > a").not.toBeVisible();
    await hover("#D2.dropdown");
    expect("#D1 > .dropdown-toggle").toHaveClass("show");
    expect("#D1 > .dropdown-menu > a").toBeVisible();
    expect("#D2 > .dropdown-toggle").not.toHaveClass("show");
    expect("#D2 > .dropdown-menu > a").not.toBeVisible();
});
