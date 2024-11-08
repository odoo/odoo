import { expect, test } from "@odoo/hoot";

import { startInteractions, setupInteractionWhiteList } from "../../core/helpers";
import { pointerDown, hover } from "@odoo/hoot-dom";

setupInteractionWhiteList("website.mega_menu_dropdown");

test("mega_menu_dropdown does nothing if there is no header#top", async () => {
    const { core } = await startInteractions(`
      <div></div>
    `);
    expect(core.interactions.length).toBe(0);
});

test("mega_menu_dropdown activate when there is a header#top", async () => {
    const { core } = await startInteractions(`
      <header id="top"></header>
    `);
    expect(core.interactions.length).toBe(1);
});

test("move from desktop to mobile (mousedown)", async () => {
    const { core, el } = await startInteractions(`
        <header id="top">
            <nav class="o_header_desktop">
                <div class="dropdown">
                    <a class="dropdown-toggle o_mega_menu_toggle"></a>
                    <div class="dropdown-menu o_mega_menu"></div>
                </div>
            </nav>
            <nav class="o_header_mobile">
                <div class="dropdown">
                    <a class="dropdown-toggle o_mega_menu_toggle"></a>
                </div>
            </nav>
        </header>
    `);
    const desktopNav = el.querySelector("nav.o_header_desktop");
    const mobileNav = el.querySelector("nav.o_header_mobile");
    const aNav = mobileNav.querySelector("a.o_mega_menu_toggle");
    await pointerDown(aNav);
    expect(!!desktopNav.querySelector('div.o_mega_menu')).toBe(false);
    expect(!!mobileNav.querySelector('div.o_mega_menu')).toBe(true);
});

test("move from mobile to desktop (mousedown)", async () => {
    const { core, el } = await startInteractions(`
        <header id="top">
            <nav class="o_header_desktop">
                <div class="dropdown">
                    <a class="dropdown-toggle o_mega_menu_toggle"></a>
                </div>
            </nav>
            <nav class="o_header_mobile">
                <div class="dropdown">
                    <a class="dropdown-toggle o_mega_menu_toggle"></a>
                    <div class="dropdown-menu o_mega_menu"></div>
                </div>
            </nav>
        </header>
    `);
    const desktopNav = el.querySelector("nav.o_header_desktop");
    const mobileNav = el.querySelector("nav.o_header_mobile");
    const aNav = desktopNav.querySelector("a.o_mega_menu_toggle");
    await pointerDown(aNav);
    expect(!!desktopNav.querySelector('div.o_mega_menu')).toBe(true);
    expect(!!mobileNav.querySelector('div.o_mega_menu')).toBe(false);
});

test("DO NOT move from desktop to mobile (hover)", async () => {
    const { core, el } = await startInteractions(`
        <header id="top" class="o_hoverable_dropdown">
            <nav class="o_header_desktop">
                <div class="dropdown">
                    <a class="dropdown-toggle o_mega_menu_toggle"></a>
                    <div class="dropdown-menu o_mega_menu"></div>
                </div>
            </nav>
            <nav class="o_header_mobile">
                <div class="dropdown">
                    <a class="dropdown-toggle o_mega_menu_toggle"></a>
                </div>
            </nav>
        </header>
    `);
    const desktopNav = el.querySelector("nav.o_header_desktop");
    const mobileNav = el.querySelector("nav.o_header_mobile");
    const aNav = mobileNav.querySelector("a.o_mega_menu_toggle");
    await hover(aNav);
    expect(!!desktopNav.querySelector('div.o_mega_menu')).toBe(true);
    expect(!!mobileNav.querySelector('div.o_mega_menu')).toBe(false);
});

test("move from mobile to desktop (hover)", async () => {
    const { core, el } = await startInteractions(`
        <header id="top" class="o_hoverable_dropdown">
            <nav class="o_header_desktop">
                <div class="dropdown">
                    <a class="dropdown-toggle o_mega_menu_toggle"></a>
                </div>
            </nav>
            <nav class="o_header_mobile">
                <div class="dropdown">
                    <a class="dropdown-toggle o_mega_menu_toggle"></a>
                    <div class="dropdown-menu o_mega_menu"></div>
                </div>
            </nav>
        </header>
    `);
    const desktopNav = el.querySelector("nav.o_header_desktop");
    const mobileNav = el.querySelector("nav.o_header_mobile");
    const aNav = desktopNav.querySelector("a.o_mega_menu_toggle");
    await hover(aNav);
    expect(!!desktopNav.querySelector('div.o_mega_menu')).toBe(true);
    expect(!!mobileNav.querySelector('div.o_mega_menu')).toBe(false);
});
