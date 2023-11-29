/** @odoo-module */
import { Component, useEffect, useRef, useState, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { makeDraggableHook } from "@web/core/utils/draggable_hook_builder_owl";
import { Reactive } from "@web/core/utils/reactive";
import { TourCompiler, findStepTriggers } from "@web_tour/tour_service/tour_compilers";
import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";
import { tourState } from '@web_tour/tour_service/tour_state';

const getBoundingClientRect = Element.prototype.getBoundingClientRect;
function getAbsoluteElementPosition(element) {
    const elRect = getBoundingClientRect.call(element);

    let absTop = elRect.top;
    let absLeft = elRect.left;
    let doc = element.ownerDocument;
    while (doc?.defaultView?.frameElement) {
        const iframeRect = getBoundingClientRect.call(doc.defaultView.frameElement);
        absTop += iframeRect.top;
        absLeft += iframeRect.left;
        doc = doc.defaultView?.frameElement?.ownerDocument;
    }
    return { height: elRect.height, width: elRect.width, top: absTop, left: absLeft };
}

function objectToStyle(obj) {
    return Object.entries(obj).map(([k,v]) => `${k}:${v}`).join(";")
}

const useDialogDraggable = makeDraggableHook({
    name: "useDialogDraggable",
    onWillStartDrag({ ctx, addCleanup, addStyle, getRect }) {
        const { height, width } = getRect(ctx.current.element);
        ctx.current.container = document.createElement("div");
        addStyle(ctx.current.container, {
            position: "fixed",
            top: "0",
            bottom: `${70 - height}px`,
            left: `${70 - width}px`,
            right: `${70 - width}px`,
        });
        ctx.current.element.after(ctx.current.container);
        addCleanup(() => ctx.current.container.remove());
    },
    onDrop({ ctx, getRect }) {
        const { top, left } = getRect(ctx.current.element);
        return {
            left: left - ctx.current.elementRect.left,
            top: top - ctx.current.elementRect.top,
        };
    },
});

class InteractiveTour extends Reactive {
    constructor() {
        super();

        this.mapping = new Map();
        this.mapping.set("start", { step: {}, display: false, shouldStop: true, isCurrent: true })
        this.steps = [];
    }

    registerStep(_step, params={}) {
        const step = { step: _step, shouldStop: true, ...params };
        this.mapping.set(_step, step);
        this.steps.push(step);
    }

    setStepState(_step, state) {
        const step = this.mapping.get(_step);
        Object.assign(step, state);
    }

    nextStep() {
        this._current.resolve?.()
    }

    get _current() {
        return this.steps.find(s => s.isCurrent && !s.isDone) || this.mapping.get("start");
    }

    suspend(_step) {
        const step = this.mapping.get(_step);
        if (step.isDone) {
            return;
        }
        if (!step.shouldStop) {
            return;
        }

        const prom = new Promise((_resolve) => {
            step.resolve = _resolve;
        })
        return prom;
    }
}

class InteractiveState extends Reactive {
    constructor() {
        super();
        this.currentTours = {};
    }

    getTour(tourName) {
        if (!(tourName in this.currentTours)) {
            this.currentTours[tourName] = new InteractiveTour();
        }
        return this.currentTours[tourName];
    }

    get allTours() {
        return Object.keys(this.currentTours);
    }

    removeTour(tourName) {
        delete this.currentTours[tourName];
    }
}

class HighlightOverlay extends Component {
    static template = owl.xml`
        <t t-foreach="props.overlays" t-as="overlay" t-key="overlay_index">
            <div class="bg-transparent" t-att-style="getOverlayStyle(overlay)" />
        </t>
    `;
    static props = {
        overlays: Array,
    };

    getOverlayStyle(overlay) {
        const { height, width, top, left, color } = overlay;
        const style = {
            position: "absolute",
            top: `${top}px`,
            left: `${left}px`,
            height: `${height}px`,
            width: `${width}px`,
            border: `dashed ${color}`,
            animation: "500ms infinite alternate element-size-pulse",
        };
        return objectToStyle(style);
    }
}

class TourInteraction extends Component {
    static template = "web_tour.TourInteraction";
    static props = {
        interactiveState: Object,
    };

    setup() {
        this.position = useState({ left: 0, top: 0 });
        useDialogDraggable({
            ref: { el: document },
            elements: ".o-tour-controller",
            ignore: ".o-tour-controller--active-tours, .o-tour-controller--current-tour-steps",
            edgeScrolling: { enabled: false },
            onDrop: ({ top, left }) => {
                this.position.left += left;
                this.position.top += top;
            },
        });
        const stepsContainer = useRef("stepsContainer");
        const currentStepRef = {
            get el() {
                return stepsContainer.el?.querySelector(".o-tour-controller--current-step");
            }
        }
        useEffect((currentStepEl) => {
            if (currentStepEl) {
                currentStepEl.scrollIntoView();
            }
        }, () => [currentStepRef.el])

        const overlay = useService("overlay");
        let currentOverlays = [];
        this.addOverlay = (...args) => {
            const remove = overlay.add(...args);
            currentOverlays.push(remove);
            return remove;
        };

        this.removeOverlays = () => {
            currentOverlays.forEach((fn) => fn());
            currentOverlays = [];
        };

        onWillUnmount(() => {
            this.removeOverlays();
        });

        this.localState = useState({ shownTour: this.activeTours[0], isExpanded: true })
    }

    get state() {
        return this.props.interactiveState;
    }

    showTour(tourName) {
        this.localState.shownTour = tourName
    }

    toggleCollapse() {
        this.localState.isExpanded = !this.localState.isExpanded;
    }

    get currentTour() {
        if (!this.localState.shownTour) {
            return null;
        }
        return this.state.getTour(this.localState.shownTour)
    }

    get activeTours() {
        return this.state.allTours;
    }

    get contentStyle() {
        const { top, left } = this.position;
        const style = {
            top: `${top}px`,
            left: `${left}px`,
            "z-index": "9999",
            opacity: "0.8",
            "max-height": `${this.maxContainerHeight}px`,
        }
        return objectToStyle(style);
    }

    getTour(tourName) {
        return this.state.getTour(tourName);
    }

    get maxContainerHeight() {
        return 0.8 * window.innerHeight;
    }

    toggleSuspend(step) {
        step.shouldStop = !step.shouldStop;
    }

    getStepClass(step) {
        if (step.isDone) {
            return "bg-success";
        }
        if (step.isCurrent) {
            return "bg-primary o-tour-controller--current-step";
        }
        if (step.shouldStop) {
            return "bg-info";
        }
    }

    onStepTriggerMouseOver(step, mode = "add") {
        if (mode !== "add") {
            this.removeOverlays();
            return;
        }
        const { triggerEl, altEl, extraTriggerOkay, skipEl } = findStepTriggers(step.step);

        const overlays = [];
        const triggerColors = ["purple", "green", "blue", "teal"];
        [triggerEl, altEl, extraTriggerOkay, skipEl].forEach((el) => {
            const color = triggerColors.shift();
            if (!el || el === true) {
                return;
            }
            const overlay = getAbsoluteElementPosition(el);
            overlay.color = color;
            overlays.push(overlay);
        });

        if (overlays.length) {
            this.addOverlay(HighlightOverlay, { overlays });
        }
    }

    playUntil(_step) {
        const tour = this.currentTour;
        let shouldStop = false;
        tour.steps.forEach(step => {
            if (step === _step) {
                shouldStop = true;
            }
            step.shouldStop = shouldStop;
        })
    }
}

const tourInteractionService = {
    dependencies: ["overlay"],
    start(env, { overlay }) {
        const currentUrlParams = new URL(window.location).searchParams;
        if (currentUrlParams.get("watch") !== "1") {
            return;
        }

        const interactiveState = new InteractiveState();
        overlay.add(TourInteraction, { interactiveState });

        patch(TourCompiler.prototype, {
            setup() {
                this.options = { ...this.options };
                this.interactiveTour = interactiveState.getTour(this.tour.name);

                const onTourEnd = this.options.onTourEnd;
                this.options.onTourEnd = (...args) => {
                    interactiveState.removeTour(this.tour.name);
                    onTourEnd(...args);
                };

                const compileStep = this.compileStep;
                this.compileStep = (stepIndex, step) => {
                    const compiled = compileStep(stepIndex, step);
                    return this._bindMacroStepToState(step, compiled);
                };
            },

            compileTourToMacro() {
                const currentStepIndex = tourState.get(this.tour.name, "currentIndex");
                if (currentStepIndex) {
                    const { filteredSteps } = this.options;
                    for (let i = 0; i < currentStepIndex; i++) {
                        this.interactiveTour.registerStep(filteredSteps[i], { isDone: true, shouldStop: false })
                    } 
                }
                return super.compileTourToMacro(...arguments);
            },

            _bindMacroStepToState(tourStep, macroStep) {
                this.interactiveTour.registerStep(tourStep);

                macroStep.unshift({
                    action: () =>
                        this.interactiveTour.setStepState(tourStep, {
                            isCurrent: true,
                        }),
                }, {
                    action: () => this.interactiveTour.suspend(tourStep)
                });

                macroStep.push({
                    action: () => {
                        this.interactiveTour.setStepState(tourStep, {
                            isDone: true,
                            isCurrent: false,
                        });
                    },
                });
                return macroStep;
            }
        });
    },
};
registry.category("services").add("tour_interaction", tourInteractionService);
