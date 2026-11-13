import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";

setupInteractionWhiteList(["website.map", "website.facebook_page", "website.instagram_page"]);

describe.current.tags("interaction_dev");

const getMapTemplate = function ({ attributes = "", withIframe = true } = {}) {
    const iframe = withIframe
        ? `<iframe class="s_map_embedded o_not_editable" src="about:blank"></iframe>`
        : "";
    return `
        <section class="s_map" data-map-address="Grand Place, Brussels" data-map-type="m" data-map-zoom="12" data-need-cookies-approval="true" ${attributes}>
            <div class="map_container">
                ${iframe}
                <div class="s_map_color_filter"></div>
            </div>
        </section>
    `;
};

test("map iframe is named after its address", async () => {
    const { core } = await startInteractions(getMapTemplate());
    expect(".s_map_embedded").toHaveAttribute("title", "Map of Grand Place, Brussels");

    core.stopInteractions();
    expect(".s_map_embedded").not.toHaveAttribute("title");
});

test("map iframe is named after the description set by the user", async () => {
    await startInteractions(
        getMapTemplate({ attributes: `data-accessible-name="Our Brussels office"` })
    );
    expect(".s_map_embedded").toHaveAttribute("title", "Our Brussels office");
});

test("reconstructed map iframe is named", async () => {
    await startInteractions(getMapTemplate({ withIframe: false }));
    expect(".s_map_embedded").toHaveAttribute("title", "Map of Grand Place, Brussels");
});

test("facebook iframe is named after its page", async () => {
    await startInteractions(`
        <section class="o_facebook_page" data-href="https://www.facebook.com/Odoo" data-height="500" data-need-cookies-approval="true"></section>
    `);
    expect(".o_facebook_page iframe").toHaveAttribute("title", "Facebook page: Odoo");
    expect(".o_facebook_page iframe").not.toHaveAttribute("aria-label");
});

test("instagram iframe is named after its account", async () => {
    await startInteractions(`
        <section class="s_instagram_page" data-instagram-page="odoo.official" data-need-cookies-approval="true">
            <div class="o_container_small o_instagram_container o_not_editable"></div>
        </section>
    `);
    expect(".o_instagram_container iframe").toHaveAttribute(
        "title",
        "Instagram account @odoo.official"
    );
    expect(".o_instagram_container iframe").not.toHaveAttribute("aria-label");
});
