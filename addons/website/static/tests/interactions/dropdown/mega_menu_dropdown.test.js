import {
    startInteractions,
    setupInteractionWhiteList,
} from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
import { hover, pointerDown } from "@odoo/hoot-dom";

setupInteractionWhiteList("website.mega_menu_dropdown");

describe.current.tags("interaction_dev");

const getTemplate = function (options = {}) {
    const contentInDesktop = options.contentInDesktop || true;
    const dropdownHoverable = options.dropdownHoverable || false;
    return `
    <header id="top">
        <nav class="o_header_desktop ${dropdownHoverable ? "o_hoverable_dropdown" : ""}">
            <div class="dropdown">
                <a class="dropdown-toggle o_mega_menu_toggle"></a>
                ${contentInDesktop ? `<div class="dropdown-menu o_mega_menu"></div>` : ""}
            </div>
        </nav>
        <nav class="o_header_mobile">
            <div class="dropdown">
                <a class="dropdown-toggle o_mega_menu_toggle"></a>
                ${contentInDesktop ? "" : `<div class="dropdown-menu o_mega_menu"></div>`}
            </div>
        </nav>
    </header>
    `
};

test("mega_menu_dropdown is started when there is an element header#top", async () => {
    const { core } = await startInteractions(getTemplate());
    expect(core.interactions).toHaveLength(1);
});

test.tags("desktop")("[mousedown] moves content from desktop to mobile", async () => {
    const { el } = await startInteractions(getTemplate({ contentInDesktop: true }));
    const desktopNav = el.querySelector("nav.o_header_desktop");
    const mobileNav = el.querySelector("nav.o_header_mobile");

    await pointerDown(mobileNav.querySelector("a.o_mega_menu_toggle"));

    expect(!!desktopNav.querySelector("div.o_mega_menu")).toBe(false);
    expect(!!mobileNav.querySelector("div.o_mega_menu")).toBe(true);
});

test.tags("desktop")("[mousedown] moves content from mobile to desktop", async () => {
    const { el } = await startInteractions(getTemplate({ contentInDesktop: false }));
    const desktopNav = el.querySelector("nav.o_header_desktop");
    const mobileNav = el.querySelector("nav.o_header_mobile");

    await pointerDown(desktopNav.querySelector("a.o_mega_menu_toggle"));

    expect(!!desktopNav.querySelector("div.o_mega_menu")).toBe(true);
    expect(!!mobileNav.querySelector("div.o_mega_menu")).toBe(false);
});

test.tags("desktop")("[hover] does not move content from desktop to mobile", async () => {
    const { el } = await startInteractions(getTemplate({ contentInDesktop: true, dropdownHoverable: true }));
    const desktopNav = el.querySelector("nav.o_header_desktop");
    const mobileNav = el.querySelector("nav.o_header_mobile");

    await hover(mobileNav.querySelector("a.o_mega_menu_toggle"));

    expect(!!desktopNav.querySelector("div.o_mega_menu")).toBe(true);
    expect(!!mobileNav.querySelector("div.o_mega_menu")).toBe(false);
});

test.tags("desktop")("[hover] moves content from mobile to desktop", async () => {
    const { el } = await startInteractions(getTemplate({ contentInDesktop: false, dropdownHoverable: true }));
    const desktopNav = el.querySelector("nav.o_header_desktop");
    const mobileNav = el.querySelector("nav.o_header_mobile");

    await hover(desktopNav.querySelector("a.o_mega_menu_toggle"));

    expect(!!desktopNav.querySelector("div.o_mega_menu")).toBe(true);
    expect(!!mobileNav.querySelector("div.o_mega_menu")).toBe(false);
});
