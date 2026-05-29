import { Component } from "@odoo/owl";
import { useRef, useState } from "@web/owl2/utils";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { makeDraggableHook } from "@web/core/utils/draggable_hook_builder_owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { TourInteractivePointer } from "../tour_interactive/tour_interactive_pointer";
import { TourInteractiveObserver } from "../tour_interactive/tour_interactive_observer";
import { isVisible } from "@web/core/utils/ui";
import { queryFirst } from "@odoo/hoot-dom";
import { tourState } from "@web_tour/js/tour_state";
import { TourAutomatic } from "../tour_automatic/tour_automatic";

const useTourPlayerDraggable = makeDraggableHook({
    name: "useTourPlayerDraggable",
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

export class TourPlayer extends Component {
    static props = {
        tour: { type: Object },
        onClose: { type: Function },
    };
    static template = "web_tour.TourPlayer";
    static components = { Dropdown, DropdownItem };

    setup() {
        this.dialog = useService("dialog");
        this.tourPlayerRef = useRef("tour_player");
        this.waiting = false;
        this.pointer = new TourInteractivePointer({
            services: {
                overlay: useService("overlay"),
                popover: useService("popover"),
                orm: useService("orm"),
                ui: useService("ui"),
            },
            autoScroll: true,
        });

        this.tour = new TourAutomatic(this.props.tour);

        window.addEventListener(
            "pointerdown",
            (ev) => {
                if (ev.target.closest(".o_tour_player")) {
                    ev.stopPropagation();
                    ev.stopImmediatePropagation();
                    ev.preventDefault();
                }
            },
            { capture: true }
        );

        this.state = useState({
            currentTrigger: false,
            position: {
                x: 0,
                y: 0,
            },
        });

        useTourPlayerDraggable({
            ref: this.tourPlayerRef,
            elements: ".o_tour_player",
            handle: ".o_tour_player_handler",
            cursor: "grabbing",
            edgeScrolling: { enabled: false },
            onDrop: ({ bottom, left }) => {
                this.state.position.x += left;
                this.state.position.y -= bottom;
            },
        });

        this.tour.start();
        while (!this.currentStep.active) {
            tourState.setCurrentIndex(this.currentStepIndex + 1);
        }

        this.destStepIndex = 0;

        this.observer = new TourInteractiveObserver(() => this.checkForCurrentTrigger());
        this.observer.observe(document.body);
    }

    get currentStepIndex() {
        return this.tour.currentIndex;
    }

    get currentStep() {
        return this.tour.currentStep;
    }

    async checkForCurrentTrigger() {
        this.state.currentTrigger = this.currentStep.findTrigger();
        if (this.state.currentTrigger instanceof Element && isVisible(this.state.currentTrigger)) {
            this.pointer.pointTo(this.state.currentTrigger, {
                content: `run: ${this.currentStep.run || "check only"}`,
                tooltipPosition: this.currentStep.position,
                hideButton: true,
            });
        } else {
            this.pointer.remove();
        }
    }

    async next() {
        await this.tour.macro.start();

        if (this.tour.macro.isComplete) {
            this.clearAll();
            return;
        }

        await this.checkForCurrentTrigger();
        if (this.currentStepIndex < this.destStepIndex) {
            await this.next();
        }
    }

    async forward() {
        const stepsLeft = this.tour.steps.slice(this.currentStepIndex);
        this.destStepIndex = stepsLeft.some((s) => s.pause)
            ? stepsLeft.findIndex((s) => s.pause) + this.currentStepIndex + 1
            : this.tour.steps.length;
        await this.next();
    }

    async jumpTo(stepIndex) {
        this.destStepIndex = stepIndex;
        await this.next();
    }

    close() {
        this.dialog.add(ConfirmationDialog, {
            title: _t("Close tour player?"),
            body: _t(
                "Are you sure you want to close the tour player?\nThis will stop the current tour."
            ),
            confirmLabel: _t("Close player"),
            cancelLabel: _t("Cancel"),
            confirm: () => {
                this.tour.end();
                this.clearAll();
            },
            cancel: () => {},
        });
    }

    clearAll() {
        this.observer.disconnect();
        this.pointer.remove();
        this.props.onClose();
    }

    onDropdownStepOpened() {
        const currentStep = queryFirst(`tr[data-key='${this.currentStepIndex}']`);
        currentStep.scrollIntoView({ behavior: "smooth", block: "center" });
    }
}
