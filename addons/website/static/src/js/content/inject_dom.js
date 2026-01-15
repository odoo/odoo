import { session } from "@web/session";
import {
    setUtmsHtmlDataset,
    getClosestLiEls,
    unhideConditionalElements,
} from "@website/utils/misc";

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

    document
        .querySelectorAll(".o_mega_menu > section.o_snippet_desktop_invisible")
        .forEach((el) => el.closest("li").classList.add("hidden_mega_menu_li"));

    const mobileInvisibleMegaMenuLiEls = getClosestLiEls(
        ".o_mega_menu > section.o_snippet_mobile_invisible"
    );
    if (!mobileInvisibleMegaMenuLiEls.length) {
        return;
    }

    // Since Mega Menus are located in the desktop header at first, we need
    // to get the indices of the mega menu elements to hide the correct one
    // in mobile
    const desktopMegaMenuLiEls = getClosestLiEls(
        "header#top nav:not(.o_header_mobile) .o_mega_menu_toggle"
    );
    const mobileMegaMenuLiEls = getClosestLiEls(
        "header#top nav.o_header_mobile .o_mega_menu_toggle"
    );
    for (const mobileInvisibleMegaMenuLiEl of mobileInvisibleMegaMenuLiEls) {
        const index = desktopMegaMenuLiEls.indexOf(mobileInvisibleMegaMenuLiEl);
        mobileMegaMenuLiEls[index].classList.add("hidden_mega_menu_li");
    }
});
