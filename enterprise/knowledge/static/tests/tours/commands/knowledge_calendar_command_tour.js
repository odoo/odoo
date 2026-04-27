/** @odoo-module */

import { registry } from "@web/core/registry";
import {
    embeddedViewPatchFunctions,
    endKnowledgeTour,
    openCommandBar,
} from "../knowledge_tour_utils.js";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import { patch } from "@web/core/utils/patch";
import { animationFrame, hover, queryFirst } from "@odoo/hoot-dom";

const embeddedViewPatchUtil = embeddedViewPatchFunctions();

function mockDate() {
    const now = "2025-02-15T08:00:00";
    class MockDate extends Date {
        static now() {
            return new Date(now);
        }
    }
    return patch(window, { Date: MockDate });
}

let unpatchDate;

function clickDate(el) {
    const rect = el.getBoundingClientRect();
    const eventParams = {
        bubbles: true,
        clientX: rect.left + 3,
        clientY: rect.top + 3,
    };
    el.dispatchEvent(new MouseEvent('mousedown', eventParams));
    el.dispatchEvent(new MouseEvent('mouseup', eventParams));
}

function dragDate(el, target) {
    // Cannot use drag_and_drop because it uses the center of the elements
    const elRect = el.getBoundingClientRect();
    el.dispatchEvent(new MouseEvent('mousedown', {
        bubbles: true,
        clientX: elRect.left + 1,
        clientY: elRect.top + 1,
    }));
    const targetRect = target.getBoundingClientRect();
    target.dispatchEvent(new MouseEvent('mousemove', {
        bubbles: true,
        clientX: targetRect.left + 1,
        clientY: targetRect.top + 1,
    }));
    target.dispatchEvent(new MouseEvent('mouseup', {
        bubbles: true,
        clientX: targetRect.left + 1,
        clientY: targetRect.top + 1,
    }));
}

registry.category("web_tour.tours").add('knowledge_calendar_command_tour', {
    url: '/odoo',
    steps: () => [stepUtils.showAppsMenuItem(), { // open the Knowledge App
    trigger: '.o_app[data-menu-xmlid="knowledge.knowledge_menu_root"]',
    run: "click",
}, {
    trigger: "body",
    run: () => {
        embeddedViewPatchUtil.before();
        unpatchDate = mockDate();
    },
}, {
    //-----------------------------------------------
    // Insert a new item calendar view in the article
    //-----------------------------------------------

    // Open the command bar
    trigger: '.odoo-editor-editable > p',
    run: function () {
        openCommandBar(this.anchor);
    },
}, { // Click on the /calendar command
    trigger: '.o-we-command-name:contains("Calendar")',
    run: 'click',
}, { // As the article does not have properties definitions, it should create default ones
    trigger: '.modal-footer .btn-primary',
    run: "click",
}, { // Scroll to the embedded view to load it
    trigger: '[data-embedded="view"]',
    run: function() {
        this.anchor.scrollIntoView(true);
    }
},
{
    trigger:
        "[data-embedded='view']",
},
{
    //---------------------------------------------------
    // Create an article item by clicking in the calendar
    //---------------------------------------------------

    // Click on a date
    trigger: '.fc-timegrid-slot.fc-timegrid-slot-lane[data-time="08:00:00"]',
    run: function () {
        clickDate(this.anchor);
    },
},
{
    trigger: ".o_hierarchy_article_name input:empty",
},
{
    // Check we created an item with the right datetime used as property
    trigger: '.o_knowledge_properties_field .o_property_field:contains("Start Date")',
    run: function () {
        const input = this.anchor.querySelector("input");
        if (!input.value.includes("08:00:00")) {
            throw new Error('Item was not created with the correct property value');
        }
    },
}, { // Set the name of the item
    trigger: '.o_knowledge_editor .odoo-editor-editable h1',
    run: "editor Item Article",
}, { // Go back to parent article
    trigger: '.o_knowledge_tree .o_article_name:contains("EditorCommandsArticle")',
    run: 'click',
}, { // Check that the item is shown in the calendar
    trigger: '.fc-timegrid-event .o_event_title:contains("Item Article")',
}, {
    //--------------------------------------------------------------
    // Insert another item calendar view (to test advanced settings)
    // and create new start and stop properties to use by the view
    //--------------------------------------------------------------

    content: "Remove previous item calendar view",
    trigger: '.odoo-editor-editable',
    run: "editor ",
},
{
    trigger: ".odoo-editor-editable:not(:has( [data-embedded='view']))",
},
{
    // Click on the "Create Item Calednar" helper
    trigger: '.o_knowledge_helper .o_knowledge_add_item_calendar',
    run: 'click',
}, { // Open the start date dropdown
    trigger: '.o_knowledge_item_calendar_dialog_date_start .o_select_menu_toggler',
    run: 'click',
}, { // Create a new start property
    trigger: '.o_select_menu_menu input',
    run: "edit Start Property",
}, {
    trigger: '.o_select_menu_menu .o_select_menu_item.o_create_datetime',
    run: 'click',
}, { // Open the stop dropwdown
    trigger: '.o_knowledge_item_calendar_dialog_date_stop .o_select_menu_toggler',
    run: 'click',
}, { // Create a new stop property
    trigger: '.o_select_menu_menu input',
    run: "edit Stop Property",
}, {
    trigger: '.o_select_menu_menu .o_select_menu_item.o_create_choice',
    run: 'click',
}, { // Change the min slot time
    trigger: ".o_knowledge_item_calendar_dialog_slot_min_time input",
    run: function () {
        this.anchor.value = "08:00";
        this.anchor.dispatchEvent(new Event("change"));
    },
}, { // Change the max slot time
    trigger: ".o_knowledge_item_calendar_dialog_slot_max_time input",
    run: function () {
        this.anchor.value = "16:30";
        this.anchor.dispatchEvent(new Event("change"));
    },
}, { // Hide Weekends
    trigger: "input[type='checkbox']",
    run: "click"
}, { // Insert the calendar
    trigger: '.modal-footer .btn-primary',
    run: 'click',
},
{
    trigger:
        "[data-embedded='view'] .o_knowledge_article_view_calendar_embedded_view",
}, { // Check that the display options are applied
    trigger: ".fc-timegrid-slots:not(:has(.fc-timegrid-slot-lane[data-time='07:00:00']))",
}, {
    trigger: ".fc-timegrid-slot.fc-timegrid-slot-lane[data-time='08:00:00']",
}, {
    trigger: ".fc-timegrid-slots:not(:has(.fc-timegrid-slot-lane[data-time='16:30:00']))",
}, {
    trigger: ".fc-timegrid-slot.fc-timegrid-slot-lane[data-time='16:00:00']",
}, {
    trigger: ".o_calendar_widget:not(:has(.fc-day-sat, .fc-day-sun))",
},
{
    //---------------------------------------------------
    // Create an article item by clicking in the calendar
    //---------------------------------------------------

    // Click on a date
    trigger: '.fc-timegrid-slot.fc-timegrid-slot-lane[data-time="08:00:00"]',
    run: function () {
        clickDate(this.anchor);
    },
},
{
    trigger: ".o_hierarchy_article_name input:empty",
},
{
    // Check we created an item with the right datetime used as property
    trigger: '.o_knowledge_properties_field .o_property_field:contains("Start Property")',
    run: function () {
        const input = this.anchor.querySelector("input");
        if (!input.value.includes("08:00:00")) {
            throw new Error('Item was not created with the correct property value');
        }
    },
}, {
    //-----------------------------------------------------------------------
    // Create new properties from the article view that will be used later in
    // this tour
    //-----------------------------------------------------------------------

    // Create a new date property
    trigger: '.o_knowledge_properties_field .o_field_property_add button',
    run: 'click',
}, {
    trigger: '.o_field_property_definition_header',
    run: "edit Date Property",
}, {
    trigger: '.o_field_property_definition_type button.dropdown-toggle',
    run: 'click',
}, {
    trigger: '.dropdown-menu .dropdown-item:contains("Date"):not(:contains("Time"))',
    run: 'click',
}, {
    trigger: '.o_knowledge_editor .odoo-editor-editable',
    run: 'click',
}, { // Create a new checkbox property
    trigger: '.o_knowledge_properties_field .o_field_property_add button',
    run: 'click',
}, {
    trigger: '.o_field_property_definition_header',
    run: "edit Boolean Property",
}, {
    trigger: '.o_field_property_definition_type button.dropdown-toggle',
    run: 'click',
}, {
    trigger: '.dropdown-menu .dropdown-item:contains("Checkbox")',
    run: 'click',
}, {
    trigger: '.o_knowledge_editor .odoo-editor-editable',
    run: 'click',
}, { // Create a text property
    trigger: '.o_knowledge_properties_field .o_field_property_add button',
    run: 'click',
}, {
    trigger: '.o_field_property_definition_header',
    run: "edit Text Property",
}, {
    trigger: '.o_field_property_definition_type button.dropdown-toggle',
    run: 'click',
}, {
    trigger: '.dropdown-menu .dropdown-item:contains("Text")',
    run: 'click',
}, {
    trigger: '.o_knowledge_editor .odoo-editor-editable',
    run: 'click',
}, { // Set the text property
    trigger: '.o_knowledge_properties_field .o_property_field:contains("Text Property") input',
    run: 'edit Custom text && click body',
}, { // Set the name of the item
    trigger: '.o_knowledge_editor .odoo-editor-editable h1',
    run: "editor Item Article",
}, { // Go back to parent article
    trigger: '.o_knowledge_tree .o_article_name:contains("Article Items")',
    run: 'click',
}, { // Check that the item is shown in the calendar
    trigger: '.fc-timegrid-event .o_event_title:contains("Item Article")',
}, {
    //-------------------------------------------------------------------------
    // Test the props editor dialog by changing the values, check that the view
    // is updated accordingly, and set the start and stop dates back to check
    // that the item article is shown again
    //-------------------------------------------------------------------------

    // Open the view props editor
    trigger: '.o_control_panel_breadcrumbs_actions .dropdown-toggle',
    run: 'click',
}, {
    trigger: '.dropdown-item:contains(Edit)',
    run: "click",
}, { // Change the start property
    trigger: '.o_knowledge_item_calendar_dialog_date_start .o_select_menu_toggler',
    run: 'click',
}, {
    trigger: '.o_select_menu_menu .o_select_menu_item:contains("Date Property")',
    run: 'click',
}, { // Check that stop date has been removed as the start type changed,
    trigger: '.o_knowledge_item_calendar_dialog_date_stop .o_select_menu_toggler_slot span.text-muted',
}, { // Open the stop property dropdown
    trigger: '.o_knowledge_item_calendar_dialog_date_stop .o_select_menu_toggler',
    run: 'click',
}, { // Check that one cannot use the selected start date
    trigger: '.o_knowledge_item_calendar_dialog_date_stop .o_select_menu:not(:contains("Date Property"))',
}, { // Don't select a stop property
    trigger: '.o_knowledge_item_calendar_props_dialog',
    run: 'click',
}, { // Open the color property dropdown
    trigger: '.o_color .o_select_menu_toggler',
    run: 'click',
}, { // Select the previously created property
    trigger: '.o_select_menu_menu .o_select_menu_item:contains("Boolean Property")',
    run: 'click',
}, { // Open the scale dropdown
    trigger: '.o_scale .o_select_menu_toggler',
    run: 'click',
}, { // Select the month scale
    trigger: '.o_select_menu_menu .o_select_menu_item:contains("Month")',
    run: 'click',
}, { // Save changes
    trigger: '.modal-footer .btn-primary',
    run: 'click',
},
{
    trigger: ".fc-view:not(:has(.fc-event-container))",
},
{
    // Check calendar has been updated (new scale and no item shown)
    trigger: '.o_knowledge_article_view_calendar_embedded_view .o_calendar_header .o_view_scale_selector:contains("Month")',
}, { // Change start and stop dates again
    trigger: '.o_control_panel_breadcrumbs_actions .dropdown-toggle',
    run: 'click',
}, {
    trigger: '.dropdown-item:contains(Edit)',
    run: "click",
}, { // Change the start property
    trigger: '.o_knowledge_item_calendar_dialog_date_start .o_select_menu_toggler',
    run: 'click',
}, {
    trigger: '.o_select_menu_menu .o_select_menu_item:contains("Start Property")',
    run: 'click',
}, { // Check that stop date has been removed as the start type changed,
    trigger: '.o_knowledge_item_calendar_dialog_date_stop .o_select_menu_toggler_slot span.text-muted',
}, { // Open the stop property dropdown
    trigger: '.o_knowledge_item_calendar_dialog_date_stop .o_select_menu_toggler',
    run: 'click',
}, { // Select the stop date
    trigger: '.o_select_menu_menu .o_select_menu_item:contains("Stop Property")',
    run: 'click',
}, { // Save changes
    trigger: '.modal-footer .btn-primary',
    run: 'click',
}, { // Open the view
    trigger: '.o_control_panel_breadcrumbs_actions .dropdown-toggle',
    run: 'click',
}, {
    trigger: '.dropdown-item:contains(Open)',
    run: "click",
},
{
    trigger: ".o_knowledge_article_view_calendar_embedded_view.o_action",
},
{
    // Check that the item is shown
    trigger: '.fc-view .o_event_title:contains("Item Article")',
}, { // Leave the app and come back to make sure that changes have been saved
    trigger: '.o_main_navbar .o_menu_toggle',
    run: "click",
}, {
    trigger: '.o_app[data-menu-xmlid="knowledge.knowledge_menu_root"]',
    run: 'click',
},
{
    trigger: "[data-embedded='view']",
},
{
    //----------------------------
    // Move the item and resize it
    //----------------------------

    // Change the scale from the calendar view
    trigger: '.o_knowledge_article_view_calendar_embedded_view .o_calendar_header .o_view_scale_selector button:contains("Month")',
    run: 'click',
}, {
    trigger: '.o-dropdown--menu .o_scale_button_week',
    run: 'click',
}, { // Move the item in the calendar
    trigger: '.fc-timegrid-event .o_event_title:contains("Item Article")',
    run: function () {
        const target = document.querySelector('.fc-timegrid-slot.fc-timegrid-slot-lane[data-time="09:00:00"]');
        dragDate(this.anchor, target);
    },
}, { // Resize the item
    trigger: '.fc-timegrid-event:contains("Item Article")',
    run: async () => {
        // Make resizer visible
        await hover(`.fc-event-main:first`, { root: this.anchor });
        await animationFrame();
        const resizer = queryFirst(`.fc-event-resizer-end`, { root: this.anchor });
        Object.assign(resizer.style, {
            display: "block",
            height: "1px",
            bottom: "0",
        });
        const target = queryFirst('.fc-timegrid-slot.fc-timegrid-slot-lane[data-time="11:00:00"]');
        dragDate(resizer, target);
    },
}, {
    //----------------------------------------------------------------------
    // Check that the date properties have been updated correctly after that
    // the item has been moved in the item calendar view, and that the text
    // property has not been changed
    //----------------------------------------------------------------------

    // Open the item
    trigger: '.fc-timegrid-event',
    run: 'dblclick',
},
{
    trigger: '.o_hierarchy_article_name input:value("Item Article")',
},
{
    // Check that the properties have been updated
    trigger: '.o_knowledge_properties_field .o_property_field:contains("Start Property")',
    run: function () {
        const input = this.anchor.querySelector("input");
        if (!input.value.includes("09:00:00")) {
            console.error('Item start date property has not been updated');
        }
    },
}, {
    trigger: '.o_knowledge_properties_field .o_property_field:contains("Stop Property")',
    run: function () {
        const input = this.anchor.querySelector("input");
        // When resizing an event, the event spans the hovered row, so we need to add 15 minutes
        if (!input.value.includes("11:15:00")) {
            console.error('Item stop date property has not been updated');
        }
    },
}, { // Check text property did not change
    trigger: '.o_knowledge_properties_field .o_property_field:contains("Text Property")',
    run: function () {
        const input = this.anchor.querySelector("input");
        if (!input.value.includes("Custom text")) {
            console.error('Item text property has changed');
        }
    },
}, {
    //---------------------------------------------------------------------
    // Remove start property to test the behavior of the item calendar view
    // when the required props are missing
    //---------------------------------------------------------------------

    // Click on edit property button
    trigger: ".o_knowledge_properties_field .o_property_field:contains(Start Property)",
    run: "hover && click .o_knowledge_properties_field .o_property_field:contains(Start Property) .o_field_property_open_popover",
}, { // Delete start date property
    trigger: '.o_field_property_definition .o_field_property_definition_delete',
    run: 'click',
}, { // Confirm deletion
    trigger: '.modal-dialog .btn-primary',
    run: 'click',
}, { // Go back to parent article
    trigger: '.o_knowledge_tree .o_article_name:contains("Article Items")',
    run: 'click',
}, { // Make sure view is not crashed and shows nocontent helper
    trigger: '.o_knowledge_article_view_calendar_embedded_view .o_knowledge_item_calendar_nocontent',
}, {
    trigger: 'body',
    run: () => {
        unpatchDate();
        embeddedViewPatchUtil.after();
    },
}, ...endKnowledgeTour()
]});
