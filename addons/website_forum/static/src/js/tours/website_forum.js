import { _t } from "@web/core/l10n/translation";
import {
    registerBackendAndFrontendTour,
} from '@website/js/tours/tour_utils';

registerBackendAndFrontendTour("question", {
    url: '/forum/1',
}, () => [{
    trigger: ".o_wforum_ask_btn",
    tooltipPosition: "left",
    content: _t("Create a new post in this forum by clicking on the button."),
    run: "click",
}, {
    trigger: "input[name=post_name]",
    tooltipPosition: "top",
    content: _t("Give your post title."),
    run: "edit Test",
},
{
    isActive: ["auto"],
    trigger: `input[name=post_name]:not(:empty)`,
},
{
    trigger: ".note-editable p",
    content: _t("Put your question here."),
    tooltipPosition: "bottom",
    run: "editor Test",
},
{
    isActive: ["auto"],
    trigger: `.note-editable p:not(:contains(/^<br>$/))`,
},
{
    trigger: ".o_select_menu_toggler",
    content: _t("Insert tags related to your question."),
    tooltipPosition: "top",
    run: "click",
}, 
{
    trigger: ".o_select_menu_sticky",
    run: "edit Test",
},
{
    isActive: ["auto"],
    trigger: `.o_popover input.o_select_menu_sticky:not(:contains(Please enter 2 or more characters))`,
},
{
    content: "Select found select menu item",
    trigger: ".o_popover.o_select_menu_menu .o_select_menu_item span:contains('Test')",
    run: 'click',
},
{
    content: "Close search bar",
    trigger: "body",
    run: 'click',
},
{
    trigger: "button:contains(/^Post/)",
    content: _t("Click to post your question."),
    tooltipPosition: "bottom",
    run: "click",
},
{
    trigger: ".o_wforum_content_wrapper h3:contains(test)",
},
{
    isActive: ["auto"],
    trigger: ".modal .modal-header button.btn-close",
    run: "click",
},
{
    trigger: "a:contains(Reply).collapsed",
    content: _t("Click to reply."),
    tooltipPosition: "bottom",
    run: "click",
},
{
    trigger: ".note-editable p",
    content: _t("Put your answer here."),
    tooltipPosition: "bottom",
    run: "editor Test",
},
{
    isActive: ["auto"],
    trigger: `.note-editable p:not(:contains(/^<br>$/))`,
},
{
    trigger: "button:contains(\"Post Answer\")",
    content: _t("Click to post your answer."),
    tooltipPosition: "bottom",
    run: "click",
}, 
{
    trigger: ".o_wforum_content_wrapper h3:contains(test)",
},
{
    isActive: ["auto"],
    trigger: ".modal:contains(thanks for posting!) .modal-header button.btn-close",
    run: "click",
}, {
    trigger: ".o_wforum_validate_toggler[data-karma]:first",
    content: _t("Click here to accept this answer."),
    tooltipPosition: "right",
    run: "click",
}, {
    isActive: ["auto"],
    content: "Check edit button is there",
    trigger: "a:contains('Edit your answer')",
}]);
