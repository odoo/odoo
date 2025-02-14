import { loadBundle } from "@web/core/assets";
import { browser } from "@web/core/browser/browser";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";

import {
    onMounted,
    onPatched,
    onWillStart,
    onWillUnmount,
    useComponent,
    useExternalListener,
    useRef,
} from "@odoo/owl";

export function useCalendarPopover(component) {
    const owner = useComponent();
    let popoverClass = "";
    const popoverOptions = { position: "right", onClose: cleanup };
    Object.defineProperty(popoverOptions, "popoverClass", { get: () => popoverClass });
    const popover = usePopover(component, popoverOptions);
    const dialog = useService("dialog");
    let removeDialog = null;
    let fcPopover;
    useExternalListener(
        window,
        "mousedown",
        (ev) => {
            if (fcPopover) {
                // do not let fullcalendar popover close when our own popover is open
                ev.stopPropagation();
            }
        },
        { capture: true }
    );
    function cleanup() {
        fcPopover = null;
        removeDialog = null;
    }
    function close() {
        removeDialog?.();
        popover.close();
        cleanup();
    }
    return {
        close,
        open(target, props, popoverClassToUse) {
            fcPopover = target.closest(".fc-popover");
            if (owner.env.isSmall) {
                close();
                removeDialog = dialog.add(component, props, { onClose: cleanup });
            } else {
                popoverClass = popoverClassToUse;
                popover.open(target, props);
            }
        },
    };
}

export function useClickHandler(singleClickCb, doubleClickCb) {
    const component = useComponent();
    let clickTimeoutId = null;
    return function handle(...args) {
        if (clickTimeoutId) {
            doubleClickCb.call(component, ...args);
            browser.clearTimeout(clickTimeoutId);
            clickTimeoutId = null;
        } else {
            clickTimeoutId = browser.setTimeout(() => {
                singleClickCb.call(component, ...args);
                clickTimeoutId = null;
            }, 250);
        }
    };
}

export function useFullCalendar(refName, params) {
    const component = useComponent();
    const ref = useRef(refName);
    let instance = null;

    function boundParams() {
        const newParams = {};
        for (const key in params) {
            const value = params[key];
            newParams[key] = typeof value === "function" ? value.bind(component) : value;
        }
        return newParams;
    }

    onWillStart(async () => await loadBundle("web.fullcalendar_lib"));

    onMounted(() => {
        try {
            instance = new FullCalendar.Calendar(ref.el, boundParams());
            instance.render();
        } catch (e) {
            throw new Error(`Cannot instantiate FullCalendar\n${e.message}`);
        }

        // Add custom time dot
        const todayCol = ref.el.querySelector(".fc-day-today.fc-timegrid-col");
        const indicatorLine = ref.el.querySelector(".fc-timegrid-now-indicator-line");

        if (todayCol && indicatorLine) {
            const indicatorToday = document.createElement("div");
            indicatorToday.className = "o_calendar_time_indicator_today";
            todayCol.appendChild(indicatorToday);

            const updateindicatorToday = () => {
                const indicatorLineStyles = window.getComputedStyle(indicatorLine);
                indicatorToday.style.top = indicatorLineStyles.getPropertyValue('top');
            };

            updateindicatorToday();

            const observer = new MutationObserver(updateindicatorToday);
            observer.observe(indicatorLine, {
                attributes: true,
                attributeFilter: ['style']
            });
        }
    });

    onPatched(() => {
        instance.refetchEvents();
        instance.setOption("weekends", component.props.isWeekendVisible);
        if (params.weekNumbers && component.props.model.scale === "year") {
            instance.destroy();
            instance.render();
        }
    });
    onWillUnmount(() => {
        instance.destroy();
    });

    return {
        get api() {
            return instance;
        },
        get el() {
            return ref.el;
        },
    };
}
