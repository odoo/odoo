import { loadJS } from "@web/core/assets";
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

    async function loadJsFiles() {
        const files = [
            "/web/static/lib/fullcalendar/core/index.global.js",
            "/web/static/lib/fullcalendar/interaction/index.global.js",
            "/web/static/lib/fullcalendar/daygrid/index.global.js",
            "/web/static/lib/fullcalendar/timegrid/index.global.js",
            "/web/static/lib/fullcalendar/list/index.global.js",
            "/web/static/lib/fullcalendar/luxon3/index.global.js",
        ];
        for (const file of files) {
            await loadJS(file);
        }
    }

    onWillStart(() => loadJsFiles());

    onMounted(() => {
        try {
            instance = new FullCalendar.Calendar(ref.el, boundParams());
            instance.render();
        } catch (e) {
            throw new Error(`Cannot instantiate FullCalendar\n${e.message}`);
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
