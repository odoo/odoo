/** @odoo-module **/

import wTourUtils from "@website/js/tours/tour_utils";

// The purpose of this tour is to check that the public widgets of snippets
// are well destroyed when their associated HTML is removed by an history undo
// and well restarted when the HTML is added again by an history redo.

wTourUtils.registerWebsitePreviewTour("test_public_widget_history", {
    test: true,
    url: "/",
    edition: true,
}, () => [
    wTourUtils.dragNDrop({
        name: "Title",
    }),
    {
        content: "Wait for public widget start and undo",
        trigger: "button.fa-undo:not([disabled])",
        extra_trigger: "iframe body.test_public_widget_running",
    },
    {
        content: "Wait for the public widget to be destroyed and redo",
        trigger: "button.fa-repeat:not([disabled])",
        extra_trigger: "iframe body:not(.test_public_widget_running)",
    },
    {
        content: "Check that the public widget is starting again",
        trigger: "iframe body.test_public_widget_running",
        isCheck: true,
    },
]);


odoo.loader.bus.addEventListener("module-started", (e) => {
    if (e.detail.moduleName !== "@website/../tests/tours/public_widget_history"
        && odoo.loader.modules.get("@web/legacy/js/public/public_widget")) {
        const publicWidget =
            odoo.loader.modules.get("@web/legacy/js/public/public_widget")[Symbol.for("default")];

        publicWidget.registry["test_public_widget"] = publicWidget.Widget.extend({
            selector: "#wrap section",
            disabledInEditableMode: false,

            /**
             * @override
             */
            start() {
                document.body.classList.add("test_public_widget_running");
                return this._super(...arguments);
            },
            /**
             * @override
             */
            destroy() {
                document.body.classList.remove("test_public_widget_running");
                return this._super(...arguments);
            }
        });
    }
});
