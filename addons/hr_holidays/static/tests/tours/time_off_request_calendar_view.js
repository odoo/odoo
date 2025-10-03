import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add("time_off_request_calendar_view", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Open Time Off app",
            trigger: '.o_app[data-menu-xmlid="hr_holidays.menu_hr_holidays_root"]',
            run: "click",
        },
        {
            content: "Click on the first Thursday of the year",
            trigger: ".fc-daygrid-day.fc-day-thu",
            run: () => {
                const el = document.querySelector(".fc-daygrid-day.fc-day-thu").firstChild;
                el.scrollIntoView();

                const fromPosition = el.getBoundingClientRect();
                fromPosition.x += el.offsetWidth / 2;
                fromPosition.y += el.offsetHeight / 2;

                el.dispatchEvent(
                    new MouseEvent("mousedown", {
                        bubbles: true,
                        which: 1,
                        button: 0,
                        clientX: fromPosition.x,
                        clientY: fromPosition.y,
                    })
                );
                el.dispatchEvent(
                    new MouseEvent("mouseup", {
                        bubbles: true,
                        which: 1,
                        button: 0,
                        clientX: fromPosition.x,
                        clientY: fromPosition.y,
                    })
                );
            },
        },
        {
            content: "Save the leave",
            trigger: '.btn:contains("Submit Request")',
            run: "click",
        },
    ],
});

function simulateDragAndDrop(sourceElement, targetElement, options = {}) {
    const { top = true, offsetX = 1, offsetY = 1 } = options;

    const sourceRect = sourceElement.getBoundingClientRect();
    const targetRect = targetElement.getBoundingClientRect();
    const startX = sourceRect.left + (sourceRect.width / 2);
    const startY = top ? sourceRect.top : sourceRect.bottom;
    const endX = targetRect.left + (offsetX || 1);
    const endY = targetRect.top + (offsetY || 1);

    sourceElement.dispatchEvent(new MouseEvent('mousedown', {
        bubbles: true,
        clientX: startX,
        clientY: startY,
    }));

    targetElement.dispatchEvent(new MouseEvent('mousemove', {
        bubbles: true,
        clientX: endX,
        clientY: endY,
    }));

    targetElement.dispatchEvent(new MouseEvent('mouseup', {
        bubbles: true,
        clientX: endX,
        clientY: endY,
    }));
}

registry.category("web_tour.tours").add("timeoff_calendar_move_leave_to_next_day_tour", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Open Time Off app",
            trigger: '.o_app[data-menu-xmlid="hr_holidays.menu_hr_holidays_root"]',
            run: "click",
        },
        {
            content: "Open dropdown to change view",
            trigger: ".o-dropdown:contains('Year')",
            run: "click",
        },
        {
            content: "Select Week view",
            trigger: '.o-dropdown-item:contains("Week")',
            run: "click",
        },
        {
            content: "Wait a bit to ensure the view is loaded",
            trigger: ".fc-day-sun .fc-event .fc-event-main",
        },
        {
            content: "Drag Sunday Leave to Monday",
            trigger: ".fc-day-sun .fc-event",
            run: function () {
                const sundayEvent = document.querySelector('.fc-day-sun .fc-event');
                const mondayTarget = document.querySelector('.fc-day-mon .fc-daygrid-day-events');
                simulateDragAndDrop(sundayEvent, mondayTarget);
            }
        },
        {
            content: "Drag Tuesday Leave to Wednesday",
            trigger: ".fc-day-tue .fc-event",
            run: function () {
                const tuesdayEvent = document.querySelector('.fc-day-tue .fc-event');
                const wednesdayTarget = document.querySelector('.fc-day-wed .fc-daygrid-day-events');
                simulateDragAndDrop(tuesdayEvent, wednesdayTarget);
            }
        },
        {
            content: "Drag Thursday Leave to Friday",
            trigger: ".fc-day-thu .fc-event",
            run: async function () {
                const thursdayEvent = document.querySelector('.fc-day-thu .fc-event');
                const fridayTarget = document.querySelector('.fc-day-fri .fc-daygrid-day-events');
                simulateDragAndDrop(thursdayEvent, fridayTarget);
            }
        },
        {
            content: "Wait a bit to ensure changes are saved",
            trigger: "body",
            run: async function () {
                await new Promise(resolve => setTimeout(resolve, 500));
            }
        },
    ]
});

registry.category("web_tour.tours").add("timeoff_calendar_resize_leave_duration_tour", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Open Time Off app",
            trigger: '.o_app[data-menu-xmlid="hr_holidays.menu_hr_holidays_root"]',
            run: "click",
        },
        {
            content: "Open dropdown to change view",
            trigger: ".o-dropdown:contains('Year')",
            run: "click",
        },
        {
            content: "Select Week view",
            trigger: '.o-dropdown-item:contains("Week")',
            run: "click",
        },
        {
            content: "Wait a bit to ensure the view is loaded",
            trigger: ".fc-day-sun .fc-event .fc-event-main",
        },
        {
            content: "Resize Sunday Leave to end at 14:00",
            trigger: '.fc-day-sun .fc-timegrid-event',
            run: async function() {
                const resizer = this.anchor.querySelector(`.fc-day-sun .fc-event-resizer-end`);
                Object.assign(resizer.style, {
                    display: "block",
                    height: "5px",
                    bottom: "0",
                });
                const target = document.querySelector('.fc-timegrid-slot.fc-timegrid-slot-lane[data-time="14:00:00"]');
                simulateDragAndDrop(resizer, target, { top: false, offsetY: -1 });
            }
        },
        {
            content: "Wait a bit to ensure changes are saved",
            trigger: "body",
            run: async function () {
                await new Promise(resolve => setTimeout(resolve, 500));
            }
        },
    ]
});
