import { useComponent, useEffect, useRef } from "@odoo/owl";
import { SIDE_PANEL_MODES } from "@web/views/calendar/calendar_side_panel/calendar_side_panel";

/**
 * Add a square selection into FullCalendar
 */
export function useSquareSelection() {
    const component = useComponent();
    const calendarRef = useRef("fullCalendar");
    const state = {};

    useEffect(
        (el, mode) => {
            if (mode !== SIDE_PANEL_MODES.filter) {
                component.fc.api.setOption("editable", false);
                component.fc.api.setOption("selectable", false);
                component.fc.api.setOption("dateClick", () => {});
            } else {
                const options = component.options;
                component.fc.api.setOption("editable", options.editable);
                component.fc.api.setOption("selectable", options.selectable);
                component.fc.api.setOption("dateClick", options.dateClick.bind(component));
            }

            clearState();

            if (mode !== SIDE_PANEL_MODES.filter) {
                window.addEventListener("pointerdown", pointerDown);
                window.addEventListener("pointermove", pointerMove);
                window.addEventListener("pointerup", pointerUp);
                window.addEventListener("pointercancel", pointerCancel);
                return () => {
                    window.removeEventListener("pointerdown", pointerDown);
                    window.removeEventListener("pointermove", pointerMove);
                    window.removeEventListener("pointerup", pointerUp);
                    window.removeEventListener("pointercancel", pointerCancel);
                };
            }
        },
        () => [calendarRef.el, component.props.sidePanelMode]
    );

    function getElementIndex(element) {
        return [].indexOf.call(element?.parentNode.children || [], element);
    }

    function clearState() {
        state.startCol = -1;
        state.endCol = -1;
        state.startRow = -1;
        state.endRow = -1;

        state.currentSelectionElement = [];
    }

    function getSelectedElement() {
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
            return calendarRef.el.querySelectorAll(elementsToSelect.join(","));
        } else {
            return [];
        }
    }

    function drawHighlight() {
        const highlight = "o-highlight";

        calendarRef.el.querySelectorAll(`.${highlight}`).forEach((node) => {
            node.classList.remove(highlight);
        });

        state.currentSelectionElement.forEach((node) => {
            node.classList.add(highlight);
        });
    }

    function pointerDown(ev) {
        const avoidElement = ev.target.closest(".fc-event, .fc-more-cell, .fc-more-popover");
        const targetElement = ev.target.closest(".fc-day:not(.fc-col-header-cell)");
        if (avoidElement || !targetElement) {
            return;
        }
        document.activeElement?.blur(); // Force blur on activeElement to force update value
        const rowSelector = 'tr[role="row"]';
        state.startCol = state.endCol = getElementIndex(targetElement);
        state.startRow = state.endRow = getElementIndex(targetElement.closest(rowSelector));
        state.currentSelectionElement = [targetElement];
        drawHighlight();
    }

    function pointerMove(ev) {
        const targetElement = ev.target.closest(".fc-day:not(.fc-col-header-cell)");
        if (!targetElement || state.startCol < 0 || state.startRow < 0) {
            return;
        }
        const rowSelector = 'tr[role="row"]';
        state.endCol = getElementIndex(targetElement);
        state.endRow = getElementIndex(targetElement.closest(rowSelector));
        state.currentSelectionElement = getSelectedElement();
        drawHighlight();
    }

    async function pointerUp(ev) {
        const targetElement = ev.target.closest(".fc-day:not(.fc-col-header-cell)");
        if (!targetElement) {
            clearState();
            drawHighlight();
            return;
        }
        if (state.currentSelectionElement.length > 0) {
            await onSquareSelection(state.currentSelectionElement);
        }
        clearState();
        drawHighlight();
    }

    function pointerCancel(ev) {
        clearState();
        drawHighlight();
    }

    async function onSquareSelection(currentSelectionElement) {
        if (component.props.sidePanelMode === SIDE_PANEL_MODES.add) {
            const dates = [];
            for (const element of currentSelectionElement) {
                const date = luxon.DateTime.fromISO(element.dataset.date);
                if (!date.invalid) {
                    dates.push(date);
                }
            }
            await component.props.multiCreateRecords(dates);
        } else if (component.props.sidePanelMode === SIDE_PANEL_MODES.delete) {
            const ids = [];
            for (const element of currentSelectionElement) {
                for (const event of [...element.querySelectorAll(".fc-event")]) {
                    ids.push(parseInt(event.dataset.eventId, 10));
                }
            }
            await component.props.multiDeleteRecords(ids);
        }
    }
}
