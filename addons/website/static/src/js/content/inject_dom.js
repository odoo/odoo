import { session } from "@web/session";
import { setUtmsHtmlDataset, unhideConditionalElements } from "@website/utils/misc";

// TODO: remove this export after refactor of `slides_course_fullscreen_player.js`
// into Interaction
export { unhideConditionalElements };

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
