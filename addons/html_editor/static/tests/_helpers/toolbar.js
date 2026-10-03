import { queryFirst, waitFor } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { contains } from "@web/../tests/web_test_helpers";

/**
 * Expands the toolbar, unless it opened expanded (see MIN_HIDDEN_FOR_COMPACT).
 */
export async function expandToolbar() {
    await waitFor(".o-we-toolbar[data-namespace]");
    if (!queryFirst(".o-we-toolbar[data-namespace='expanded']")) {
        await contains(".o-we-toolbar .btn[name='expand_toolbar'").click();
    }
    await waitFor(".o-we-toolbar[data-namespace='expanded']");
}

/**
 * Opens a toolbar menu (see `isMenu` toolbar items), unless it is already
 * open. Selecting an item closes the menu.
 *
 * @param {string} menuId
 */
export async function openToolbarMenu(menuId) {
    await animationFrame();
    if (!queryFirst(".o-we-toolbar-menu")) {
        await contains(`.o-we-toolbar .btn[name='${menuId}']`).click();
    }
    return waitFor(".o-we-toolbar-menu");
}
