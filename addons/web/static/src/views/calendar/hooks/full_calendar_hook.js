import { loadBundle } from "@web/core/assets";

import {
    onMounted,
    onPatched,
    onWillStart,
    onWillUnmount,
    signal,
    untrack,
    useProps,
} from "@odoo/owl";

/**
 * @param {import("@odoo/owl").Signal<HTMLElement>} ref
 * @param {any} params
 */
export function useFullCalendar(ref, params) {
    const props = useProps();
    const instance = signal(null);

    onWillStart(() => loadBundle("web.fullcalendar_lib"));

    onMounted(() => {
        try {
            instance.set(new FullCalendar.Calendar(untrack(ref), params));
            instance().render();
        } catch (e) {
            throw new Error(`Cannot instantiate FullCalendar\n${e.message}`);
        }
    });

    onPatched(() => {
        instance().refetchEvents();
        instance().setOption("weekends", props.isWeekendVisible);
        if (params.weekNumbers && props.model.scale === "year") {
            instance().destroy();
            instance().render();
        }
    });
    onWillUnmount(() => {
        instance().destroy();
    });

    return {
        get api() {
            return instance();
        },
        get el() {
            return untrack(ref);
        },
    };
}
