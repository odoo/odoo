/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.websiteEventTemplatePatch = publicWidget.Widget.extend({
    selector: ".o_wevent_events_list",

    start() {
        // hack to make event short description editable,
        // can be removed in master.
        const eventEls = this.el.querySelectorAll("small[itemprop='description']");
        eventEls.forEach((eventEl) => {
            const id = eventEl.parentElement
                .querySelector("span[itemprop='name']")
                .getAttribute("data-oe-id");
            eventEl.classList.remove("o_not_editable");
            eventEl.dataset.oeModel = "event.event";
            eventEl.dataset.oeField = "subtitle";
            eventEl.dataset.oeType = "char";
            eventEl.dataset.oeId = id;
        });
    },
});

export default publicWidget.registry.websiteEventTemplatePatch;
