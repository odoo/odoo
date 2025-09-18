// @ts-check

/** @module @web/views/calendar/hooks/full_calendar_hook - Hook managing FullCalendar instance lifecycle (load, render, refresh, destroy) */

import {
    onMounted,
    onPatched,
    onWillStart,
    onWillUnmount,
    useComponent,
    useRef,
} from "@odoo/owl";
/**
 * OWL hook that manages a FullCalendar instance lifecycle.
 *
 * Loads the FullCalendar library bundle, creates and renders the calendar on
 * mount, refreshes events on patch, and destroys the instance on unmount.
 *
 * @param {string} refName - OWL template ref name for the calendar container element
 * @param {Object} params - FullCalendar configuration options (functions are bound to the component)
 * @returns {{ api: FullCalendar.Calendar, el: HTMLElement }} accessor for the calendar instance and DOM element
 */
import { loadBundle } from "@web/core/assets";
export function useFullCalendar(refName, params) {
    const component = useComponent();
    const ref = useRef(refName);
    let instance = null;

    function boundParams() {
        const newParams = {};
        for (const key in params) {
            const value = params[key];
            newParams[key] =
                typeof value === "function" ? value.bind(component) : value;
        }
        return newParams;
    }

    onWillStart(async () => await loadBundle("web.fullcalendar_lib"));

    onMounted(() => {
        try {
            instance = new FullCalendar.Calendar(ref.el, boundParams());
            instance.render();
        } catch (e) {
            throw new Error(`Cannot instantiate FullCalendar\n${e.message}`, {
                cause: e,
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
