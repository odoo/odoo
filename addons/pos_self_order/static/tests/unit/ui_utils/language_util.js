import { animationFrame, waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";

export async function openLanguageSelector() {
    await contains(".o_self_language_selector").click();
    await animationFrame();
}

export async function changeLanguage(language) {
    await openLanguageSelector();
    await contains(`.self_order_language_popup .btn:contains(${language})`).click();
    await waitFor(`.o_self_language_selector:contains(${language})`);
    await animationFrame();
}

export async function checkLanguageSelected(language) {
    await waitFor(`.o_self_language_selector:contains("${language}")`);
}

export async function checkCountryFlagShown(country_code) {
    await waitFor(`.o_self_language_selector > img[src*=${country_code}]`);
}
