import { expect, test } from "@odoo/hoot";

import {
    startInteractions,
    setupInteractionWhiteList,
} from "../../core/helpers";

import { hover, leave } from "@odoo/hoot-dom";

setupInteractionWhiteList("website.hoverable_dropdown");

const getTemplate = function (options = {}) {
    return `
        <header class="o_hoverable_dropdown" style="display: flex; height: 50px; background-color: #CCFFCC;">
            <div style="margin: 10px;">
                <span>Hello World<span>
            </div>
            <div class="dropdown" style="margin: 10px;">
                Dropdown
                <a class="dropdown-toggle"></a>
                <div class="dropdown-menu">
                    <a href="#" style="display: block;">A</a>
                    <a href="#" style="display: block;">B</a>
                    <a href="#" style="display: block;">C</a>
                </div>
            </div>
        </header>
        <main style="height: 100px; background-color: #FFCCCC">
            <span style="margin: 10px;">Main</span>
        </main>
    `
}

test("hoverable_dropdown is started when there is an element header.o_hoverable_dropdown", async () => {
    const { core } = await startInteractions(getTemplate());
    expect(core.interactions.length).toBe(1);
});

test.tags("desktop")("[hover] show / hide dropdown content", async () => {
    const { el } = await startInteractions(getTemplate());
    const dropdownEl = el.querySelector(".dropdown");
    const dropdownMenuEl = el.querySelector(".dropdown-menu");
    const dropdownToggleEl = el.querySelector(".dropdown-toggle");
    const aEl = dropdownMenuEl.querySelector("a");

    expect(dropdownToggleEl.classList.contains("show")).toBe(false);
    expect(aEl.checkVisibility()).toBe(false);

    await hover(dropdownEl);

    expect(dropdownToggleEl.classList.contains("show")).toBe(true);
    expect(aEl.checkVisibility()).toBe(true);

    await leave(dropdownEl);

    expect(dropdownToggleEl.classList.contains("show")).toBe(false);
    expect(aEl.checkVisibility()).toBe(false);
});
