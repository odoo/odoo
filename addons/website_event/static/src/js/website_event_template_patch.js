import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.websiteEventTemplatePatch = publicWidget.Widget.extend({
    selector: '.o_wevent_events_list',

    start() {
        // debugger
        // const eventList = this.el.querySelector("small[itemprop='description']");
        // const id = eventList.parentElement.querySelector("span[itemprop='name']").getAttribute("data-oe-id");
        // eventList.setAttribute("contenteditable", "true");
        // eventList.setAttribute("data-oe-model", "event.event");
        // eventList.setAttribute("data-oe-field", "subtitle");
        // eventList.setAttribute("data-oe-expression", "event.subtitle");
        // eventList.setAttribute("data-oe-type", "char");
        // eventList.setAttribute("data-oe-id", id);

        const eventLists = this.el.querySelectorAll("small[itemprop='description']");

        eventLists.forEach(eventList => {
        const idElement = eventList.parentElement;
        const id = idElement.querySelector("span[itemprop='name']").getAttribute("data-oe-id");

        eventList.setAttribute("contenteditable", "true");
        eventList.dataset.oeModel = "event.event";
        eventList.dataset.oeField = "subtitle";
        eventList.dataset.oeExpression = "event.subtitle";
        eventList.dataset.oeType = "char";
        eventList.dataset.oeId = id;
});

    }
});

export default publicWidget.registry.websiteEventTemplatePatch;
