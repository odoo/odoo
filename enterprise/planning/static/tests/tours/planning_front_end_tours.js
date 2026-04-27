import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('planning_front_end_tour', {
    steps: () => [{
        trigger: "button[title='Week view']",
        content: "The front end calendar should be rendered",
    }, {
        trigger: "button[title='Month view']",
        content: "Switch the calendar to month view",
        run: "click",
    }, {
        trigger: "button[title='List view']",
        content: "Switch the calendar to list view",
        run: "click",
    }, {
        trigger: "button[title='Week view']",
        content: "Switch the calendar back to week view",
        run: "click",
    }, {
        trigger: "td.fc-timegrid-col a[style='border-color: rgb(238, 75, 57); background-color: rgb(238, 75, 57);']",
        content: "Click on shift of the employee on the calendar",
        run: "click",
    }, {
        trigger: "form[id='modal_action_switch_shift'] button[type='submit']",
        content: "Click on the 'Ask to Switch' button in the popover",
        run: "click",
        expectUnloadPage: true,
    }, {
        trigger: "div.o_planning_toast.bg-success",
        content: "A success planning toast notification should appear",
    }, {
        trigger: "td.fc-timegrid-col a[style='border-color: rgb(255, 172, 0); background-color: rgb(238, 75, 57); border-width: 5px; opacity: 0.7;']",
        content: "The shift's calendar entry should have changed in style to indicate that a request to switch has been filed",
    }, {
        trigger: "div.o_planning_calendar_unwanted_shifts",
        content: "After switching a shift, the unwanted shifts section should appear",
    }, {
        trigger: "div.o_planning_calendar_unwanted_shifts td[name='buttons'] div button[type='submit']",
        content: "Click on the 'Cancel Switch' button to cancel the switch shift request",
        run: "click",
        expectUnloadPage: true,
    }, {
        trigger: "div.o_planning_calendar_open_shifts",
        content: "Since we have an open shift available, the open shifts section be rendered",
    }, {
        trigger: "div.o_planning_calendar_open_shifts td[name='buttons'] div button[type='submit']",
        content: "Click on the 'I take it' button to cancel the switch shift request",
        run: "click",
    }],
});

registry.category("web_tour.tours").add('planning_front_end_allow_unassign_tour', {
    steps: () => [{
        trigger: "td.fc-timegrid-col a[style='border-color: rgb(238, 75, 57); background-color: rgb(238, 75, 57);']",
        content: "Click on shift of the employee on the calendar",
        run: "click",
    }, {
        trigger: "form[id='modal_action_dismiss_shift'] button[type='submit']",
        content: "Click on the 'I am Unavailable' button in the popover",
        run: "click",
        expectUnloadPage: true,
    }, {
        trigger: "div.o_planning_toast.bg-success",
        content: "A success planning toast notification should appear",
    }, {
        trigger: "div.o_planning_calendar_open_shifts",
        content: "Since we have an open shift available, the open shifts section be rendered",
    }],
});

registry.category("web_tour.tours").add('planning_front_end_buttons_tour', {
    steps: () => [{
        trigger: "div.o_planning_toast.bg-success",
        content: "A success planning toast notification should appear",
    }, {
        trigger: "button[title='Week view']",
        content: "The front end calendar should be rendered",
    }, {
        trigger: "td.fc-timegrid-col a[style='border-color: rgb(242, 150, 72); background-color: rgb(242, 150, 72);']",
        content: "The slots inside the front end calendar should be rendered",
    }],
});
