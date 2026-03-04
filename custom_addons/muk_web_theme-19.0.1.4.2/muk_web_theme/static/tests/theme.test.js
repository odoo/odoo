import { expect, test } from "@odoo/hoot";

import "@muk_web_appsbar/webclient/menus/app_menu_service";
import "@muk_web_theme/webclient/navbar/navbar";

import { NavBar } from "@web/webclient/navbar/navbar";
import { AppsMenu } from "@muk_web_theme/webclient/appsmenu/appsmenu";

test.tags("muk_web_theme");
test("navbar uses AppsMenu component", async () => {
    expect(NavBar.components.AppsMenu).toBe(AppsMenu);
});
