import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { queryAll } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import {
    contains,
    defineMenus,
    getService,
    mockService,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { config as transitionConfig } from "@web/core/transition";
import { WebClient } from "@web/webclient/webclient";

describe.current.tags("mobile");
defineMailModels();

test("website custom menus are opened from the mobile app menu", async () => {
    patchWithCleanup(transitionConfig, { disabled: true });
    defineMenus([
        { id: 0 },
        {
            id: 1,
            name: "Website",
            appID: 1,
            xmlid: "website.menu_website_configuration",
            children: [
                {
                    id: 2,
                    name: "Site",
                    appID: 1,
                    xmlid: "website.menu_site",
                    children: [
                        {
                            id: 3,
                            name: "Optimize SEO",
                            appID: 1,
                            xmlid: "website.menu_optimize_seo",
                        },
                    ],
                },
            ],
        },
    ]);
    mockService("website", () => ({}));
    mockService("website_custom_menus", () => ({
        get: (xmlid) => (xmlid === "website.menu_optimize_seo" ? {} : null),
        open: (menu) => expect.step(`open ${menu.xmlid}`),
        addCustomMenus: (sections) => sections,
    }));

    await mountWithCleanup(WebClient);
    getService("menu").setCurrentMenu(1);
    await animationFrame();
    await contains("a.o_menu_toggle", { root: document.body }).click();
    await contains(".o_app_menu_sidebar li[data-menu-xmlid='website.menu_optimize_seo']", {
        root: document.body,
    }).click();

    expect.verifySteps(["open website.menu_optimize_seo"]);
    expect(queryAll(".o_app_menu_sidebar", { root: document.body })).toHaveCount(0);
});
