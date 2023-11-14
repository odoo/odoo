/** @odoo-module **/

import tour from "web_tour.tour";
import wTourUtils from "website.tour_utils";

tour.register("test_drag_and_drop_on_non_editable", {
    test: true,
    url: "/",
}, [
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    wTourUtils.dragNDrop({
        id: "s_company_team",
        name: "Team",
    }),
    {
        content: "Verify that there is an editable media in non editable env.",
        trigger: "#wrapwrap .s_company_team .o_not_editable > .o_editable_media",
        run: () => null, // it's a check
    },
    Object.assign(wTourUtils.dragNDrop({
        id: "s_text_highlight",
        name: "Text Highlight",
    }), {
        content: "Drag and drop the Text Highlight building block next to the Team block media.",
        run: "drag_and_drop #wrapwrap .s_company_team .o_not_editable > .o_editable_media",
    }),
    {
        content: "Verify that the Text Highlight building block isn't in a non editable element.",
        trigger: ".s_company_team :not(.o_not_editable) > .s_text_highlight",
        run: () => null, // it's a check
    },
]);
