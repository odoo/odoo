import { animationFrame } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";

export async function selectTicketFilter(filterName) {
    await contains(".ticket-screen .filter").click();
    await animationFrame();
    await contains(`.dropdown-item:contains("${filterName}")`).click();
    await animationFrame();
}
