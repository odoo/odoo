import { useComponent, useEffect } from "@odoo/owl";
import { CALENDAR_MODES } from "@web/views/calendar/calendar_modes";

/**
 * Add a square selection into FullCalendar using custom listener
 *
 * @param onSquareSelection {function(HTMLElement[]): Promise} callback returning selected DOM elements
 */
export function useSquareSelection(onSquareSelection) {
    const component = useComponent();

    const state = {};

    useEffect(
        (el, mode) => {
            const options = component.finalOptions(mode);
            component.fc.api.setOption("editable", options["editable"]);
            component.fc.api.setOption("selectable", options["selectable"]);
            component.fc.api.setOption("dateClick", options["dateClick"].bind(component));

            multiCreateClearState();

            if (mode !== CALENDAR_MODES.filter) {
                const multiCreatePointerDownBound = multiCreatePointerDown.bind(component);
                const multiCreatePointerMoveBound = multiCreatePointerMove.bind(component);
                const multiCreatePointerUpBound = multiCreatePointerUp.bind(component);
                const multiCreatePointerCancelBound = multiCreatePointerCancel.bind(component);
                window.addEventListener("pointerdown", multiCreatePointerDownBound);
                window.addEventListener("pointermove", multiCreatePointerMoveBound);
                window.addEventListener("pointerup", multiCreatePointerUpBound);
                window.addEventListener("pointercancel", multiCreatePointerCancelBound);
                return () => {
                    window.removeEventListener("pointerdown", multiCreatePointerDownBound);
                    window.removeEventListener("pointermove", multiCreatePointerMoveBound);
                    window.removeEventListener("pointerup", multiCreatePointerUpBound);
                    window.removeEventListener("pointercancel", multiCreatePointerCancelBound);
                };
            }
        },
        () => [component.calendarRef.el, component.props.calendarMode]
    );

    function getElementIndex(element) {
        return [].indexOf.call(element?.parentNode.children || [], element);
    }

    function multiCreateClearState() {
        state.startCol = -1;
        state.endCol = -1;
        state.startRow = -1;
        state.endRow = -1;

        state.currentSelectionElement = [];
    }

    function multiCreateGetSelectedElement() {
        const elementsToSelect = [];
        const [startX, endX] = [state.startCol, state.endCol].sort();
        const [startY, endY] = [state.startRow, state.endRow].sort();

        for (let x = startX; x <= endX; x++) {
            for (let y = startY; y <= endY; y++) {
                elementsToSelect.push(
                    `tbody tr[role="row"]:nth-child(${y + 1}) > .fc-day:nth-child(${x + 1})`
                );
            }
        }

        if (elementsToSelect.length) {
            return component.calendarRef.el.querySelectorAll(elementsToSelect.join(","));
        } else {
            return [];
        }
    }

    function multiCreateDrawHighlight() {
        const highlight = "o-highlight";

        component.calendarRef.el.querySelectorAll(`.${highlight}`).forEach((node) => {
            node.classList.remove(highlight);
        });

        state.currentSelectionElement.forEach((node) => {
            node.classList.add(highlight);
        });
    }

    function multiCreatePointerDown(ev) {
        if (component.props.calendarMode === CALENDAR_MODES.filter) {
            return;
        }
        if (ev.target.closest(".fc-event")) {
            return;
        }
        const targetElement = ev.target.closest(".fc-day:not(.fc-col-header-cell)");
        if (!targetElement) {
            return;
        }
        const rowSelector = 'tr[role="row"]';
        state.startCol = state.endCol = getElementIndex(targetElement);
        state.startRow = state.endRow = getElementIndex(targetElement.closest(rowSelector));
        state.currentSelectionElement = [targetElement];
        multiCreateDrawHighlight();
    }

    function multiCreatePointerMove(ev) {
        if (component.props.calendarMode === CALENDAR_MODES.filter) {
            return;
        }
        const targetElement = ev.target.closest(".fc-day:not(.fc-col-header-cell)");
        if (!targetElement || state.startCol < 0 || state.startRow < 0) {
            return;
        }
        const rowSelector = 'tr[role="row"]';
        state.endCol = getElementIndex(targetElement);
        state.endRow = getElementIndex(targetElement.closest(rowSelector));
        state.currentSelectionElement = multiCreateGetSelectedElement();
        multiCreateDrawHighlight();
    }

    async function multiCreatePointerUp(ev) {
        if (component.props.calendarMode === CALENDAR_MODES.filter) {
            return;
        }
        const targetElement = ev.target.closest(".fc-day:not(.fc-col-header-cell)");
        if (!targetElement) {
            multiCreateClearState();
            multiCreateDrawHighlight();
            return;
        }
        await onSquareSelection(state.currentSelectionElement);
        multiCreateClearState();
        multiCreateDrawHighlight();
    }

    function multiCreatePointerCancel(ev) {
        multiCreateClearState();
        multiCreateDrawHighlight();
    }
}
