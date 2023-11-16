/** @odoo-module */
import { Component, useState, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { makeDraggableHook } from "@web/core/utils/draggable_hook_builder";
import { Reactive } from "@web/core/utils/reactive";
import { TourCompiler, findStepTriggers } from "@web_tour/tour_service/tour_compilers";
import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";

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
        return `position: absolute;top: ${top}px;left:${left}px;height:${height}px;width:${width}px;border: dashed ${color};"`;
    }
}

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
        doc = doc.defaultView?.frameElement;
    }
    return { height: elRect.height, width: elRect.width, top: absTop, left: absLeft };
}

export class TourInteraction extends Component {
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
        return `top: ${this.position.top}px; left: ${this.position.left}px; width: 300px; z-index:9999; opacity: 0.8;cursor:move;`;
    }

    getTour(tourName) {
        return this.state.getTour(tourName);
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

class InteractiveTour extends Reactive {
    constructor() {
        super();
        this.steps = {};
    }

    registerStep(stepIndex, _step) {
        this.steps[stepIndex] = { step: _step, shouldStop: true };
    }

    setStepState(stepIndex, state) {
        Object.assign(this.steps[stepIndex], state);
    }

    nextStep() {
        this.prom.resolve();
    }

    suspend(stepIndex) {
        const step = this.steps[stepIndex];
        if (step) {
            if (step.isDone) {
                return;
            }
            if (!step.shouldStop) {
                return;
            }
        }

        let resolve;
        const prom = new Promise((_resolve) => (resolve = _resolve)).then(() => {
            if (this.prom === prom) {
                this.prom = null;
            }
        });
        prom.resolve = resolve;
        this.prom = prom;
        return prom;
    }
}

export class InteractiveState extends Reactive {
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

const tourInteractionService = {
    dependencies: ["tour_service", "overlay"],
    start(env, { overlay }) {
        const currentUrlParams = new URL(window.location).searchParams;
        if (currentUrlParams.get("watch") !== "1") {
            return;
        }

        const interactiveState = new InteractiveState();
        overlay.add(TourInteraction, { interactiveState });

        patch(TourCompiler.prototype, "TourInteractionCompiler", {
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
                    });

                    compiled.push({
                        action: async () => {
                            await this.interactiveTour.suspend(stepIndex);
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
                const macro = this._super(...arguments);
                macro.steps.unshift({
                    action: () => {
                        return this.interactiveTour.suspend("start");
                    },
                });
                return macro;
            },
        });
    },
};
registry.category("services").add("tour_interaction", tourInteractionService);
