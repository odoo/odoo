import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { browser } from "@web/core/browser/browser";
import { queryAll, queryFirst, queryOne } from "@odoo/hoot-dom";
import { Component, useState, useExternalListener, useRef } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { x2ManyCommands } from "@web/core/orm_service";
import { tourRecorderState } from "./tour_recorder_state";
import { makeDraggableHook } from "@web/core/utils/draggable_hook_builder_owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";

const PRECISE_IDENTIFIERS = ["data-menu-xmlid", "name", "contenteditable"];
const ODOO_CLASS_REGEX = /^oe?(-|_)[\w-]+$/;
const VALIDATING_KEYS = ["Enter", "Tab"];

/**
 * @param {EventTarget[]} paths composedPath of an click event
 * @returns {string}
 */
const getShortestSelector = (paths) => {
    paths.reverse();
    let filteredPath = [];
    let hasOdooClass = false;
    for (
        let currentElem = paths.pop();
        (currentElem && queryAll(filteredPath.join(" > ")).length !== 1) || !hasOdooClass;
        currentElem = paths.pop()
    ) {
        if (currentElem.parentElement.contentEditable === "true") {
            continue;
        }

        let currentPredicate = currentElem.tagName.toLowerCase();
        const odooClass = [...currentElem.classList].find((c) => c.match(ODOO_CLASS_REGEX));
        if (odooClass) {
            currentPredicate = `.${odooClass}`;
            hasOdooClass = true;
        }

        // If we are inside a link or button the previous elements, like <i></i>, <span></span>, etc., can be removed
        if (["BUTTON", "A"].includes(currentElem.tagName)) {
            filteredPath = [];
        }

        for (const identifier of PRECISE_IDENTIFIERS) {
            const identifierValue = currentElem.getAttribute(identifier);
            if (identifierValue) {
                currentPredicate += `[${identifier}='${CSS.escape(identifierValue)}']`;
            }
        }

        const siblingNodes = queryAll(":scope > " + currentPredicate, {
            root: currentElem.parentElement,
        });
        if (siblingNodes.length > 1) {
            currentPredicate += `:nth-child(${
                [...currentElem.parentElement.children].indexOf(currentElem) + 1
            })`;
        }

        filteredPath.unshift(currentPredicate);
    }

    if (filteredPath.length > 2) {
        return reducePath(filteredPath);
    }

    return filteredPath.join(" > ");
};

/**
 * @param {string[]} paths
 * @returns {string}
 */
const reducePath = (paths) => {
    const numberOfElement = paths.length - 2;
    let currentElement = "";
    let hasReduced = false;
    let path = paths.shift();
    for (let i = 0; i < numberOfElement; i++) {
        currentElement = paths.shift();
        if (queryAll(`${path} ${paths.join(" > ")}`).length === 1) {
            hasReduced = true;
        } else {
            path += `${hasReduced ? " " : " > "}${currentElement}`;
            hasReduced = false;
        }
    }
    path += `${hasReduced ? " " : " > "}${paths.shift()}`;
    return path;
};

const useTourRecorderDraggable = makeDraggableHook({
    name: "useTourRecorderDraggable",
    onWillStartDrag({ ctx, addCleanup, addStyle }) {
        ctx.current.container = document.createElement("div");
        addStyle(ctx.current.container, {
            position: "fixed",
            top: "0",
            bottom: "0",
            left: "0",
            right: "0",
        });
        ctx.current.element.after(ctx.current.container);
        addCleanup(() => ctx.current.container.remove());
    },
    onDrop({ ctx, getRect }) {
        const { bottom, left } = getRect(ctx.current.element);
        return {
            left: left - ctx.current.elementRect.left,
            bottom: bottom - ctx.current.elementRect.bottom,
        };
    },
});

export class TourRecorder extends Component {
    static template = "web_tour.TourRecorder";
    static components = { Dropdown, DropdownItem };
    static props = {
        onClose: { type: Function },
    };
    static defaultState = {
        recording: false,
        url: "",
        editedElement: undefined,
        tourName: "",
    };

    setup() {
        this.originClickEvent = false;
        this.destClickEvent = false;
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.state = useState({
            ...TourRecorder.defaultState,
            steps: [],
            position: {
                x: 0,
                y: 0,
            },
        });
        this.tourRecorderRef = useRef("tour_recorder");
        this.dropdownState = useDropdownState();

        this.state.steps = tourRecorderState.getCurrentTourRecorder();
        this.state.recording = tourRecorderState.isRecording() === "1";
        useExternalListener(document, "pointerdown", this.setStartingEvent, { capture: true });
        useExternalListener(document, "pointerup", this.onPointerUpEvent, { capture: true });
        useExternalListener(document, "click", this.recordClickEvent, { capture: true });
        useExternalListener(document, "keydown", this.recordConfirmationKeyboardEvent, {
            capture: true,
        });
        useExternalListener(document, "keyup", this.recordKeyboardEvent, { capture: true });

        useTourRecorderDraggable({
            ref: this.tourRecorderRef,
            elements: ".o_tour_recorder",
            handle: ".o_tour_recorder_handler",
            cursor: "grabbing",
            edgeScrolling: { enabled: false },
            onDrop: ({ bottom, left }) => {
                this.state.position.x += left;
                this.state.position.y -= bottom;
            },
        });
    }

    /**
     * @param {PointerEvent} ev
     */
    setStartingEvent(ev) {
        if (!this.state.recording || ev.target.closest(".o_tour_recorder")) {
            return;
        }
        this.originClickEvent = ev.composedPath().filter((p) => p instanceof Element);
    }

    onPointerUpEvent(ev) {
        if (!this.state.recording || ev.target.closest(".o_tour_recorder")) {
            return;
        }
        this.destClickEvent = ev.composedPath().filter((p) => p instanceof Element);
    }

    /**
     * @param {PointerEvent} ev
     */
    recordClickEvent(ev) {
        if (
            !this.state.recording ||
            ev.target.closest(".o_tour_recorder") ||
            (!this.originClickEvent && this.destClickEvent)
        ) {
            return;
        } else if (!this.originClickEvent && !this.destClickEvent) {
            this.originClickEvent = ev.composedPath().filter((p) => p instanceof Element);
            this.destClickEvent = this.originClickEvent;
        }
        const pathElements = this.destClickEvent;
        this.addTourStep([...pathElements]);

        const lastStepInput = this.state.steps.at(-1);
        // Check that pointerdown and pointerup paths are different to know if it's a drag&drop or a click
        if (
            JSON.stringify(pathElements.map((e) => e.tagName)) !==
            JSON.stringify(this.originClickEvent.map((e) => e.tagName))
        ) {
            lastStepInput.run = `drag_and_drop ${lastStepInput.trigger}`;
            lastStepInput.trigger = getShortestSelector(this.originClickEvent);
        } else {
            const lastStepInput = this.state.steps.at(-1);
            lastStepInput.run = "click";
        }

        tourRecorderState.setCurrentTourRecorder(this.state.steps);
        this.originClickEvent = false;
        this.destClickEvent = false;
    }

    /**
     * @param {KeyboardEvent} ev
     */
    recordConfirmationKeyboardEvent(ev) {
        if (
            !this.state.recording ||
            !this.state.editedElement ||
            ev.target.closest(".o_tour_recorder")
        ) {
            return;
        }

        if (
            [...this.state.editedElement.classList].includes("o-autocomplete--input") &&
            VALIDATING_KEYS.includes(ev.key)
        ) {
            const selectedRow = queryFirst(".ui-state-active", {
                root: this.state.editedElement.parentElement,
            });
            this.state.steps.push({
                trigger: `.o-autocomplete--dropdown-item > a:contains('${selectedRow.textContent}'), .fa-circle-o-notch`,
                run: "click",
            });
            this.state.editedElement = undefined;
        }
        tourRecorderState.setCurrentTourRecorder(this.state.steps);
    }

    /**
     * @param {KeyboardEvent} ev
     */
    recordKeyboardEvent(ev) {
        if (
            !this.state.recording ||
            VALIDATING_KEYS.includes(ev.key) ||
            ev.target.closest(".o_tour_recorder")
        ) {
            return;
        }

        if (ev.target.closest(".o_command_palette_search") && !this.state.editedElement) {
            const lastStepPalette = this.state.steps.at(-1);
            if (!lastStepPalette || lastStepPalette.trigger != "[data-menu='shortcuts']") {
                this.state.steps.push(
                    {
                        trigger: ".o_user_menu button",
                        run: "click",
                    },
                    {
                        trigger: "[data-menu='shortcuts']",
                        run: "click",
                    }
                );
            }
        }

        if (!this.state.editedElement) {
            if (
                ev.target.matches(
                    "input:not(:disabled), textarea:not(:disabled), [contenteditable=true]"
                )
            ) {
                this.state.editedElement = ev.target;
                this.state.steps.push({
                    trigger: getShortestSelector(ev.composedPath()),
                });
            } else {
                return;
            }
        }

        if (!this.state.editedElement) {
            return;
        }

        const lastStep = this.state.steps.at(-1);
        if (this.state.editedElement.contentEditable === "true") {
            lastStep.run = `editor ${this.state.editedElement.textContent}`;
        } else {
            lastStep.run = `edit ${this.state.editedElement.value}`;
        }
        tourRecorderState.setCurrentTourRecorder(this.state.steps);
    }

    toggleRecording() {
        this.state.recording = !this.state.recording;
        tourRecorderState.setIsRecording(this.state.recording);
        this.state.editedElement = undefined;
        if (this.state.recording && !this.state.url) {
            this.state.url = browser.location.pathname + browser.location.search;
        }
    }

    async saveTour() {
        const newTour = {
            name: this.state.tourName.replaceAll(" ", "_"),
            url: this.state.url,
            step_ids: this.state.steps.map((s) => x2ManyCommands.create(undefined, s)),
            custom: true,
        };

        const result = await this.orm.create("web_tour.tour", [newTour]);
        if (result) {
            const removeNotification = this.notification.add(_t("'%s' created", newTour.name), {
                type: "success",
                buttons: [
                    {
                        name: _t("View tour"),
                        onClick: () => {
                            this.action.doAction({
                                type: "ir.actions.act_window",
                                res_model: "web_tour.tour",
                                res_id: result[0],
                                views: [[false, "form"]],
                                target: "current",
                            });
                            removeNotification();
                        },
                    },
                ],
            });
            this.resetTourRecorderState();
        } else {
            this.notification.add(_t("Custom tour '%s' couldn't be saved!", newTour.name), {
                type: "danger",
            });
        }
    }

    resetTourRecorderState() {
        Object.assign(this.state, { ...TourRecorder.defaultState, steps: [] });
        tourRecorderState.clear();
    }

    /**
     * @param {Element[]} path
     */
    addTourStep(path) {
        const shortestPath = getShortestSelector(path);
        const target = queryOne(shortestPath);
        this.state.editedElement =
            target.matches(
                "input:not(:disabled), textarea:not(:disabled), [contenteditable=true]"
            ) && target;
        this.state.steps.push({
            trigger: shortestPath,
        });
    }

    removeStep(index) {
        this.state.steps.splice(index, 1);
        tourRecorderState.setCurrentTourRecorder(this.state.steps);
    }

    openResetStepsDialog() {
        this.dialog.add(ConfirmationDialog, {
            title: _t("Clear all steps?"),
            body: _t("Are you sure you want to clear all steps?\nAll steps will be lost."),
            confirmLabel: _t("Clear"),
            cancelLabel: _t("Cancel"),
            confirm: () => {
                this.resetTourRecorderState();
                this.dropdownState.close();
            },
            cancel: () => {},
        });
    }

    openCloseRecorderDialog() {
        this.dialog.add(ConfirmationDialog, {
            title: _t("Close tour recorder?"),
            body: _t(
                "Are you sure you want to close the tour recorder?\nAll changes will be lost."
            ),
            confirmLabel: _t("Close recorder"),
            cancelLabel: _t("Cancel"),
            confirm: () => {
                this.props.onClose();
            },
            cancel: () => {},
        });
    }
}
