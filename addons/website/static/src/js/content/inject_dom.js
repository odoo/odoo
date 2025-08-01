import { session } from "@web/session";
import { setUtmsHtmlDataset, unhideConditionalElements } from "@website/utils/misc";

document.addEventListener("DOMContentLoaded", () => {
    // Transfer cookie/session data as HTML element's attributes so that CSS
    // selectors can be based on them.
    setUtmsHtmlDataset();
    const htmlEl = document.documentElement;
    const country = session.geoip_country_code;
    if (country) {
        htmlEl.dataset.country = country;
    }
    htmlEl.dataset.logged = !session.is_website_user;

    unhideConditionalElements();
});
