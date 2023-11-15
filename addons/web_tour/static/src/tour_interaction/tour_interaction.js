/** @odoo-module */
import { Component, useState, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { makeDraggableHook } from "@web/core/utils/draggable_hook_builder_owl";
import { Reactive } from "@web/core/utils/reactive";
import { TourCompiler, findStepTriggers } from "@web_tour/tour_service/tour_compilers";
import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";

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
        this.steps = {
            start: { shouldStop: true, isCurrent: true, step: { absolutePosition: "start"} }
        };
        this.currentStep = "start"
    }

    registerStep(stepIndex, _step) {
        this.steps[stepIndex] = { step: _step, shouldStop: true };
    }

    setStepState(stepIndex, state) {
        Object.assign(this.steps[stepIndex], state);
    }

    nextStep() {
        this._current.resolve()
    }

    get _current() {
        const found = Object.entries(this.steps).find(([name, s]) => s.isCurrent && !s.isDone);
        return this.steps[found[0]];
    }

    suspend(stepIndex) {
        const step = this.steps[stepIndex];
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
            ignore: ".o-tour-controller--content",
            edgeScrolling: { enabled: false },
            onDrop: ({ top, left }) => {
                this.position.left += left;
                this.position.top += top;
            },
        });

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
    }

    get state() {
        return this.props.interactiveState;
    }

    get activeTours() {
        return this.state.allTours;
    }

    get contentStyle() {
        const { top, left } = this.position;
        const style = {
            top: `${top}px`,
            left: `${left}px`,
            width: "300px",
            "z-index": "9999",
            opacity: "0.8",
            cursor: "move",
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

    toggleSuspend(tourName, stepIndex) {
        const tour = this.getTour(tourName);
        const step = tour.steps[stepIndex];
        step.shouldStop = !step.shouldStop;
    }

    getStepClass(step) {
        if (step.isDone) {
            return "bg-success";
        }
        if (step.isCurrent) {
            return "bg-primary";
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

    playUntil(tourName, stepIndex) {
        const tour = this.state.getTour(tourName);
        Object.entries(tour.steps).forEach(([k, v]) => {
            v.shouldStop = k >= stepIndex;
        });
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
                    this.interactiveTour.registerStep(stepIndex, step);

                    compiled.unshift({
                        action: () =>
                            this.interactiveTour.setStepState(stepIndex, {
                                isCurrent: true,
                            }),
                    }, {
                        action: () => this.interactiveTour.suspend(stepIndex)
                    });

                    compiled.push({
                        action: () => {
                            this.interactiveTour.setStepState(stepIndex, {
                                isDone: true,
                                isCurrent: false,
                            });
                        },
                    });
                    return compiled;
                };
            },

            compileTourToMacro() {
                const macro = super.compileTourToMacro(...arguments);
                macro.steps.unshift({
                    action: () => {
                        return this.interactiveTour.suspend("start");
                    },
                }, {
                    action: () => {
                        this.interactiveTour.setStepState("start", { isDone: true, isCurrent: false})
                    }
                });
                return macro;
            },
        });
    },
};
registry.category("services").add("tour_interaction", tourInteractionService);
