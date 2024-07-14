/** @odoo-module */

import { registry } from "@web/core/registry";
import { endKnowledgeTour, openCommandBar } from '../knowledge_tour_utils.js';
import { stepUtils } from "@web_tour/tour_service/tour_utils";

function clickDate(el) {
    const rect = el.getBoundingClientRect();
    const eventParams = {
        bubbles: true,
        clientX: rect.left + 1,
        clientY: rect.top + 1,
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
    url: '/web',
    test: true,
    steps: () => [stepUtils.showAppsMenuItem(), { // open the Knowledge App
    trigger: '.o_app[data-menu-xmlid="knowledge.knowledge_menu_root"]',
}, { 
    //-----------------------------------------------
    // Insert a new item calendar view in the article
    //-----------------------------------------------
    
    // Open the command bar
    trigger: '.odoo-editor-editable > p',
    run: function () {
        openCommandBar(this.$anchor[0]);
    },
}, { // Click on the /calendar command
    trigger: '.oe-powerbox-commandName:contains("Calendar")',
    run: 'click',
}, { // As the article does not have properties definitions, it should create default ones
    trigger: '.modal-footer .btn-primary',
}, { // Scroll to the embedded view to load it
    trigger: '.o_knowledge_behavior_type_embedded_view',
    run: () => {},
}, { 
    //---------------------------------------------------
    // Create an article item by clicking in the calendar
    //---------------------------------------------------

    // Click on a date
    trigger: 'tr[data-time="08:00:00"] td.fc-widget-content:not(.fc-time)',
    extra_trigger: '.o_knowledge_behavior_type_embedded_view .o_knowledge_article_view_calendar_embedded_view',
    run: function () {
        clickDate(this.$anchor[0]);
    },
}, {
    // Check we created an item with the right datetime used as property
    trigger: '.o_knowledge_properties_field .o_property_field:contains("Start Date")',
    extra_trigger: '.o_breadcrumb_article_name_container span:empty',
    run: function () {
        const input = this.$anchor.find("input")[0];
        if (!input.value.includes("08:00:00")) {
            throw new Error('Item was not created with the correct property value');
        }
    },
}, { // Set the name of the item
    trigger: '.o_knowledge_editor .odoo-editor-editable h1',
    run: 'text Item Article',
}, { // Go back to parent article
    trigger: '.o_knowledge_tree .o_article_name:contains("EditorCommandsArticle")',
    run: 'click',
}, { // Check that the item is shown in the calendar
    trigger: '.fc-time-grid-event .o_event_title:contains("Item Article")',
    run: () => {},
}, {
    //--------------------------------------------------------------
    // Insert another item calendar view (to test advanced settings)
    // and create new start and stop properties to use by the view
    //--------------------------------------------------------------

    // Remove previous item calendar view
    trigger: '.odoo-editor-editable',
    run: function () {
        this.$anchor.data('wysiwyg').odooEditor.resetContent();
    },
}, {
    // Click on the "Create Item Calednar" helper
    trigger: '.o_knowledge_helper .o_knowledge_add_item_calendar',
    extra_trigger: '.odoo-editor-editable:not(:has(.o_knowledge_behavior_type_embedded_view))',
    run: 'click',
}, { // Open the start date dropdown
    trigger: '.o_knowledge_item_calendar_dialog_date_start .o_select_menu_toggler',
    run: 'click',
}, { // Create a new start property
    trigger: '.o_knowledge_item_calendar_dialog_date_start .o_select_menu input',
    run: 'text Start Property'
}, {
    trigger: '.o_knowledge_item_calendar_dialog_date_start .o_select_menu .o_select_menu_item.o_create_datetime',
    run: 'click',
}, { // Open the stop dropwdown
    trigger: '.o_knowledge_item_calendar_dialog_date_stop .o_select_menu_toggler',
    run: 'click',
}, { // Create a new stop property
    trigger: '.o_knowledge_item_calendar_dialog_date_stop .o_select_menu input',
    run: 'text Stop Property'
}, {
    trigger: '.o_knowledge_item_calendar_dialog_date_stop .o_select_menu .o_select_menu_item.o_create_choice',
    run: 'click',
}, { // Insert the calendar
    trigger: '.modal-footer .btn-primary',
    run: 'click',
}, {
    //---------------------------------------------------
    // Create an article item by clicking in the calendar
    //---------------------------------------------------

    // Click on a date
    trigger: 'tr[data-time="08:00:00"] td.fc-widget-content:not(.fc-time)',
    extra_trigger: '.o_knowledge_behavior_type_embedded_view .o_knowledge_article_view_calendar_embedded_view',
    run: function () {
        clickDate(this.$anchor[0]);
    },
}, {
    // Check we created an item with the right datetime used as property
    trigger: '.o_knowledge_properties_field .o_property_field:contains("Start Property")',
    extra_trigger: '.o_breadcrumb_article_name_container span:empty',
    run: function () {
        const input = this.$anchor.find("input")[0];
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
    run: 'text Date Property',
}, {
    trigger: '.o_field_property_definition_type button.dropdown-toggle',
    run: 'click',
}, {
    trigger: '.o_field_property_definition_type .dropdown-menu .dropdown-item:contains("Date"):not(:contains("Time"))',
    run: 'click',
}, {
    trigger: '.o_knowledge_editor .odoo-editor-editable',
    run: 'click',
}, { // Create a new checkbox property
    trigger: '.o_knowledge_properties_field .o_field_property_add button',
    run: 'click',
}, {
    trigger: '.o_field_property_definition_header',
    run: 'text Boolean Property',
}, {
    trigger: '.o_field_property_definition_type button.dropdown-toggle',
    run: 'click',
}, {
    trigger: '.o_field_property_definition_type .dropdown-menu .dropdown-item:contains("Checkbox")',
    run: 'click',
}, {
    trigger: '.o_knowledge_editor .odoo-editor-editable',
    run: 'click',
}, { // Create a text property
    trigger: '.o_knowledge_properties_field .o_field_property_add button',
    run: 'click',
}, {
    trigger: '.o_field_property_definition_header',
    run: 'text Text Property',
}, {
    trigger: '.o_field_property_definition_type button.dropdown-toggle',
    run: 'click',
}, {
    trigger: '.o_field_property_definition_type .dropdown-menu .dropdown-item:contains("Text")',
    run: 'click',
}, {
    trigger: '.o_knowledge_editor .odoo-editor-editable',
    run: 'click',
}, { // Set the text property
    trigger: '.o_knowledge_properties_field .o_property_field:contains("Text Property") input',
    run: 'text Custom text',
}, { // Set the name of the item 
    trigger: '.o_knowledge_editor .odoo-editor-editable h1',
    run: 'text Item Article',
}, { // Go back to parent article
    trigger: '.o_knowledge_tree .o_article_name:contains("Article Items")',
    run: 'click',
}, { // Check that the item is shown in the calendar
    trigger: '.fc-time-grid-event .o_event_title:contains("Item Article")',
    run: () => {},
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
    trigger: '.dropdown-item:contains(Edit)'
}, { // Change the start property
    trigger: '.o_knowledge_item_calendar_dialog_date_start .o_select_menu_toggler',
    run: 'click',
}, {
    trigger: '.o_knowledge_item_calendar_dialog_date_start .o_select_menu .o_select_menu_item:contains("Date Property")',
    run: 'click',
}, { // Check that stop date has been removed as the start type changed,
    trigger: '.o_knowledge_item_calendar_dialog_date_stop .o_select_menu_toggler_slot span.text-muted',
    run: () => {},
}, { // Open the stop property dropdown
    trigger: '.o_knowledge_item_calendar_dialog_date_stop .o_select_menu_toggler',
    run: 'click',
}, { // Check that one cannot use the selected start date
    trigger: '.o_knowledge_item_calendar_dialog_date_stop .o_select_menu:not(:contains("Date Property"))',
    run: () => {},
}, { // Don't select a stop property
    trigger: '.o_knowledge_item_calendar_props_dialog',
    run: 'click',
}, { // Open the color property dropdown
    trigger: '.o_color .o_select_menu_toggler',
    run: 'click',
}, { // Select the previously created property
    trigger: '.o_color .o_select_menu .o_select_menu_item:contains("Boolean Property")',
    run: 'click',
}, { // Open the scale dropdown
    trigger: '.o_scale .o_select_menu_toggler',
    run: 'click',
}, { // Select the month scale
    trigger: '.o_scale .o_select_menu .o_select_menu_item:contains("Month")',
    run: 'click',
}, { // Save changes
    trigger: '.modal-footer .btn-primary',
    run: 'click',
}, { // Check calendar has been updated (new scale and no item shown)
    trigger: '.o_knowledge_article_view_calendar_embedded_view .o_calendar_header .o_view_scale_selector:contains("Month")',
    extra_trigger: '.fc-view:not(:has(.fc-event-container))',
    run: () => {},
}, { // Change start and stop dates again
    trigger: '.o_control_panel_breadcrumbs_actions .dropdown-toggle',
    run: 'click',
}, {
    trigger: '.dropdown-item:contains(Edit)'
}, { // Change the start property
    trigger: '.o_knowledge_item_calendar_dialog_date_start .o_select_menu_toggler',
    run: 'click',
}, {
    trigger: '.o_knowledge_item_calendar_dialog_date_start .o_select_menu .o_select_menu_item:contains("Start Property")',
    run: 'click',
}, { // Check that stop date has been removed as the start type changed,
    trigger: '.o_knowledge_item_calendar_dialog_date_stop .o_select_menu_toggler_slot span.text-muted',
    run: () => {},
}, { // Open the stop property dropdown
    trigger: '.o_knowledge_item_calendar_dialog_date_stop .o_select_menu_toggler',
    run: 'click',
}, { // Select the stop date
    trigger: '.o_knowledge_item_calendar_dialog_date_stop .o_select_menu .o_select_menu_item:contains("Stop Property")',
    run: 'click',
}, { // Save changes
    trigger: '.modal-footer .btn-primary',
    run: 'click',
}, { // Open the view
    trigger: '.o_control_panel_breadcrumbs_actions .dropdown-toggle',
    run: 'click',
}, {
    trigger: '.dropdown-item:contains(Open)'
}, { // Check that the item is shown
    trigger: '.fc-view .o_event_title:contains("Item Article")',
    extra_trigger: '.o_knowledge_article_view_calendar_embedded_view.o_action',
    run: () => {},
}, { // Leave the app and come back to make sure that changes have been saved
    trigger: '.o_main_navbar .o_menu_toggle',
}, {
    trigger: '.o_app[data-menu-xmlid="knowledge.knowledge_menu_root"]',
    run: 'click',
}, { 
    //----------------------------
    // Move the item and resize it
    //----------------------------

    // Change the scale from the calendar view
    trigger: '.o_knowledge_article_view_calendar_embedded_view .o_calendar_header .o_view_scale_selector button:contains("Month")',
    extra_trigger: '.o_knowledge_behavior_type_embedded_view',
    run: 'click',
}, {
    trigger: '.o_knowledge_article_view_calendar_embedded_view .o_calendar_header .o_scale_button_week',
    run: 'click',
}, { // Move the item in the calendar
    trigger: '.fc-time-grid-event .o_event_title:contains("Item Article")',
    run: function () {
        const target = document.querySelector('tr[data-time="09:00:00"] td.fc-widget-content:not(.fc-time)');
        dragDate(this.$anchor[0], target);
    },
}, { // Make resizer visible
    trigger: '.fc-time-grid-event',
    run: function () {
        const resizer = this.$anchor.find('.fc-end-resizer')[0];
        resizer.style.display = "block";
        resizer.style.width = "100%";
        resizer.style.height = "3px";
        resizer.style.bottom = "0";
        },
}, {
    trigger: '.fc-time-grid-event:contains("Item Article") .fc-end-resizer',
    run: function () {
        const target = document.querySelector('tr[data-time="11:00:00"] td.fc-widget-content:not(.fc-time)');
        dragDate(this.$anchor[0], target);
    },
}, { 
    //----------------------------------------------------------------------
    // Check that the date properties have been updated correclty after that
    // the item has been moved in the item calendar view, and that the text
    // property has not been changed
    //----------------------------------------------------------------------

    // Open the item
    trigger: '.fc-time-grid-event',
    run: 'dblclick',
}, { // Check that the properties have been updated
    trigger: '.o_knowledge_properties_field .o_property_field:contains("Start Property")',
    extra_trigger: '.o_breadcrumb_article_name_container:contains("Item Article")',
    run: function () {
        const input = this.$anchor.find("input")[0];
        if (!input.value.includes("09:00:00")) {
            throw new Error('Item start date property has not been updated');
        }
    },
}, {
    trigger: '.o_knowledge_properties_field .o_property_field:contains("Stop Property")',
    run: function () {
        const input = this.$anchor.find("input")[0];
        // When resizing an event, the event spans the hovered row, so we need to add 15 minutes
        if (!input.value.includes("11:15:00")) {
            throw new Error('Item stop date property has not been updated');
        }
    },
}, { // Check text property did not change
    trigger: '.o_knowledge_properties_field .o_property_field:contains("Text Property")',
    run: function () {
        const input = this.$anchor.find("input")[0];
        if (!input.value.includes("Custom text")) {
            throw new Error('Item text property has changed');
        }
    },
}, {
    //---------------------------------------------------------------------
    // Remove start property to test the behavior of the item calendar view
    // when the required props are missing
    //---------------------------------------------------------------------

    // Click on edit property button
    trigger: '.o_knowledge_properties_field .o_property_field:contains("Start Property") .o_field_property_open_popover',
    run: 'click',
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
    run: () => {},
}, ...endKnowledgeTour()
]});
