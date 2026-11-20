/** @odoo-module **/

import { loadCSS, loadJS } from "@web/core/assets";
import { browser } from "@web/core/browser/browser";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";

import {
    onMounted,
    onPatched,
    onWillStart,
    onWillUnmount,
    onWillUpdateProps,
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

    async function loadJsFiles() {
        const files = [
            "/web/static/lib/fullcalendar/core/main.js",
            "/web/static/lib/fullcalendar/interaction/main.js",
            "/web/static/lib/fullcalendar/daygrid/main.js",
            "/web/static/lib/fullcalendar/luxon/main.js",
            "/web/static/lib/fullcalendar/timegrid/main.js",
            "/web/static/lib/fullcalendar/list/main.js",
        ];
        for (const file of files) {
            await loadJS(file);
        }
    }
    async function loadCssFiles() {
        await Promise.all(
            [
                "/web/static/lib/fullcalendar/core/main.css",
                "/web/static/lib/fullcalendar/daygrid/main.css",
                "/web/static/lib/fullcalendar/timegrid/main.css",
                "/web/static/lib/fullcalendar/list/main.css",
            ].map((file) => loadCSS(file))
        );
    }

    onWillStart(() => Promise.all([loadJsFiles(), loadCssFiles()]));

    onMounted(() => {
        try {
            instance = new FullCalendar.Calendar(ref.el, boundParams());
            instance.render();
        } catch (e) {
            throw new Error(`Cannot instantiate FullCalendar\n${e.message}`);
        }
    });

    let isWeekendVisible = params.isWeekendVisible;
    onWillUpdateProps((np) => {
        isWeekendVisible = np.isWeekendVisible;
    });
    onPatched(() => {
        instance.refetchEvents();
        instance.setOption("weekends", isWeekendVisible);
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
