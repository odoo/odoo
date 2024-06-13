import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { browser } from "@web/core/browser/browser";
import { queryAll, queryOne } from "@odoo/hoot-dom";
import { Component, useState, useExternalListener } from "@odoo/owl";

export class TourRecorderError extends Error {}

const PRECISE_IDENTIFIERS = ["data-menu-xmlid", "name", "contenteditable"];
const ODOO_CLASS_REGEX = /^oe?(-|_)[\w-]+$/;

/**
 * @param {Element[]} paths composedPath of an click event
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

        const siblingNodes = currentElem.parentElement.querySelectorAll(
            ":scope > " + currentPredicate
        );
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
    static template = "web_tour_recorder.TourRecorder";
    static components = { Dropdown, DropdownItem };
    static props = {};
    static defaultState = {
        recording: false,
        url: "",
        editedElement: undefined,
        tourName: "",
    };

    setup() {
        this.originClickEvent = false;
        this.tourRecorderService = useService("tour_recorder");
        this.notification = useService("notification");
        this.state = useState({
            ...TourRecorder.defaultState,
            steps: [],
            collapsed: true,
        });

        useExternalListener(document, "pointerdown", this.setStartingEvent, { capture: true });
        useExternalListener(document, "pointerup", this.recordClickEvent, { capture: true });
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
    }

    recordKeyboardEvent() {
        if (!this.state.recording || !this.state.editedElement) {
            return;
        }
        const lastStep = this.state.steps.at(-1);
        if (this.state.editedElement.contentEditable === "true") {
            lastStep.run = `editor ${this.state.editedElement.textContent}`;
        } else {
            lastStep.run = `edit ${this.state.editedElement.value}`;
        }
    }

    toggleRecording() {
        this.state.recording = !this.state.recording;
        this.state.editedElement = undefined;
        if (this.state.recording && !this.state.url) {
            this.state.url = browser.location.pathname + browser.location.search;
        }
    }

    saveTour() {
        const newTour = {
            name: this.state.tourName.replaceAll(" ", "_"),
            url: this.state.url,
            steps: this.state.steps,
            test: true,
        };

        const result = this.tourRecorderService.addCustomTour(newTour);
        if (result) {
            this.resetTourRecorderState();
        }
    }

    resetTourRecorderState() {
        Object.assign(this.state, { ...TourRecorder.defaultState, steps: [] });
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
