import {
    onMounted,
    onPatched,
    onWillStart,
    onWillUnmount,
    signal,
    useListener,
    useProps,
} from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { odooCalendarTheme } from "@web/views/calendar/calendar_theme";

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
            instance.set(
                new FullCalendar.Calendar(ref(), { plugins: [odooCalendarTheme], ...params })
            );
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
    onWillUnmount(() => instance().destroy());

    // FullCalendar measures its grid once per interaction, a resize meanwhile (e.g. the tablet
    // browser toolbar showing up while scrolling) makes its hit detection read past the last row.
    useListener(ref, "pointerdown", () => {
        const el = ref();
        el.style.minHeight = el.style.maxHeight = `${el.getBoundingClientRect().height}px`;
        const controller = new AbortController();
        const unlock = () => {
            el.style.minHeight = el.style.maxHeight = "";
            controller.abort();
        };
        const options = { capture: true, signal: controller.signal };
        window.addEventListener("pointerup", unlock, options);
        window.addEventListener("pointercancel", unlock, options);
    });

    return instance;
}
