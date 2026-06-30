import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { browser } from "@web/core/browser/browser";
import { queryAll, queryFirst, queryOne } from "@odoo/hoot-dom";
import { Component, useState, useExternalListener } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { x2ManyCommands } from "@web/core/orm_service";
import { tourRecorderState } from "./tour_recorder_state";

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
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.state = useState({
            ...TourRecorder.defaultState,
            steps: [],
        });

        this.state.steps = tourRecorderState.getCurrentTourRecorder();
        this.state.recording = tourRecorderState.isRecording() === "1";
        useExternalListener(document, "pointerdown", this.setStartingEvent, { capture: true });
        useExternalListener(document, "pointerup", this.recordClickEvent, { capture: true });
        useExternalListener(document, "keydown", this.recordConfirmationKeyboardEvent, {
            capture: true,
        });
        useExternalListener(document, "keyup", this.recordKeyboardEvent, { capture: true });
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

    /**
     * @param {PointerEvent} ev
     */
    recordClickEvent(ev) {
        if (!this.state.recording || ev.target.closest(".o_tour_recorder")) {
            return;
        }
        const pathElements = ev.composedPath().filter((p) => p instanceof Element);
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
            this.notification.add(_t("Custom tour '%s' has been added.", newTour.name), {
                type: "success",
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
}
