import { useComponent } from "@web/owl2/utils";
import { loadBundle } from "@web/core/assets";

import { onMounted, onPatched, onWillStart, onWillUnmount, untrack } from "@odoo/owl";

export function useFullCalendar(ref, params) {
    const component = useComponent();
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
            instance = new FullCalendar.Calendar(untrack(ref), boundParams());
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
            return untrack(ref);
        },
    };
}
