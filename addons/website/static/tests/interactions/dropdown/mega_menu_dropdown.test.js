import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
import { hover, pointerDown, queryFirst } from "@odoo/hoot-dom";

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
    `;
};

test("mega_menu_dropdown is started when there is an element header#top", async () => {
    const { core } = await startInteractions(getTemplate());
    expect(core.interactions).toHaveLength(1);
});

test.tags("desktop");
test("[mousedown] moves content from desktop to mobile", async () => {
    await startInteractions(getTemplate({ contentInDesktop: true }));

    await pointerDown("nav.o_header_mobile a.o_mega_menu_toggle");
    expect(queryFirst("nav.o_header_desktop div.o_mega_menu")).toBe(null);
    expect(queryFirst("nav.o_header_mobile div.o_mega_menu")).not.toBe(null);
});

test.tags("desktop");
test("[mousedown] moves content from mobile to desktop", async () => {
    await startInteractions(getTemplate({ contentInDesktop: false }));

    await pointerDown("nav.o_header_desktop a.o_mega_menu_toggle");
    expect(queryFirst("nav.o_header_desktop div.o_mega_menu")).not.toBe(null);
    expect(queryFirst("nav.o_header_mobile div.o_mega_menu")).toBe(null);
});

test.tags("desktop");
test("[hover] does not move content from desktop to mobile", async () => {
    await startInteractions(getTemplate({ contentInDesktop: true, dropdownHoverable: true }));

    await hover("nav.o_header_mobile a.o_mega_menu_toggle");
    expect(queryFirst("nav.o_header_desktop div.o_mega_menu")).not.toBe(null);
    expect(queryFirst("nav.o_header_mobile div.o_mega_menu")).toBe(null);
});

test.tags("desktop");
test("[hover] moves content from mobile to desktop", async () => {
    await startInteractions(getTemplate({ contentInDesktop: false, dropdownHoverable: true }));

    await hover("nav.o_header_desktop a.o_mega_menu_toggle");
    expect(queryFirst("nav.o_header_desktop div.o_mega_menu")).not.toBe(null);
    expect(queryFirst("nav.o_header_mobile div.o_mega_menu")).toBe(null);
});
