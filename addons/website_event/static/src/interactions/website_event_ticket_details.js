import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

export class TicketDetails extends Interaction {
    static selector = ".o_wevent_js_ticket_details";
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _envBus: () => this.env.bus,
    };
    dynamicContent = {
        _envBus: {
            "t-on-websiteEvent.enableSubmit": () => this.buttonDisabled = false,
        },
        "button[data-increment-type='minus']": {
            "t-on-mouseenter": (ev) => this.onMouseDown(ev, -1),
            "t-on-mousedown": (ev) => this.onMouseDown(ev, -1),
            "t-on-mouseup": this.onMouseUp,
            "t-on-mouseleave": this.onMouseUp,
        },
        "button[data-increment-type='plus']": {
            "t-on-mouseenter": (ev) => this.onMouseDown(ev, 1),
            "t-on-mousedown": (ev) => this.onMouseDown(ev, 1),
            "t-on-mouseup": this.onMouseUp,
            "t-on-mouseleave": this.onMouseUp,
        },
        "input[id='spinnerInputNumber']": {
            "t-on-input": this.onInput, // use updateContent() to enable/disable submit button
        },
        ".a-submit": {
            "t-on-click.prevent.stop": this.onSubmitClick,
            "t-att-disabled": () => this.noTicketsOrdered || this.buttonDisabled ? "disabled" : false,
        },
    };

    get noTicketsOrdered() {
        return Boolean(
            !Array.from(this.el.querySelectorAll("input[id='spinnerInputNumber']")).find(
                (input) => Number.isNaN(parseInt(input.value)) ? 0 : parseInt(input.value) > 0
            )
        );
    }

    setup() {
        this.firstIncrementTimeout = 350;
        this.incrementInterval = 75;
    }

    /**
     * @param {InputEvent} ev
     */
    async onInput(ev) {
        const inputComponent = ev.target;
        const maximumBound = inputComponent.max || Infinity;
        const newValue = inputComponent.value.replace(/[^0-9]/g, '');
        inputComponent.value = BigInt(Math.min(newValue, maximumBound));  // Bigint allows to avoid scientific notation
        
        const buttons = this.el.querySelectorAll(`button[data-input-name=${inputComponent.name}]`);
        buttons[0].disabled = inputComponent.value <= 0;
        buttons[1].disabled = inputComponent.value >= maximumBound;
    }

    /**
     * @param {MouseEvent} ev
     */
    async onSubmitClick(ev) {
        const formEl = ev.currentTarget.closest("form");
        this.buttonDisabled = true;
        const modal = await this.waitFor(rpc(
            formEl.action,
            Object.fromEntries(new FormData(formEl)),
        ));

        const modalEl = new DOMParser().parseFromString(modal, "text/html").body.firstChild;
        this.insert(modalEl, document.body);
    }

    /**
     * Spinner -/+ : increment ticket number while left mouse button is held
     * 
     * @param {MouseEvent} ev
     */
    onMouseDown(ev, incrementValue) {
        if (ev.buttons === 1) {
            const inputComponent = this.el.querySelector(`input[name=${ev.currentTarget.dataset.inputName}]`);
            this._ticketSpinner(inputComponent, incrementValue);
            this.spinnerTimeout = setTimeout(() => {
                this.spinnerInterval = setInterval(this._ticketSpinner, this.incrementInterval, inputComponent, incrementValue);
            }, this.firstIncrementTimeout);
        }
    }

    /**
     * @param {MouseEvent} ev
     */
    onMouseUp(ev) {
        if (ev.button === 0) {
            clearTimeout(this.spinnerTimeout);
            clearInterval(this.spinnerInterval);
        }
    }

    _ticketSpinner(inputComponent, incrementValue) {
        const maximumBound = inputComponent.max || Infinity;
        const inputValue = parseInt(inputComponent.value);
        if (0 <= inputValue && inputValue <= maximumBound) {
            inputComponent.value = Math.max(0, Math.min(inputValue + incrementValue, maximumBound));
        } else {
            inputComponent.value = inputValue < 0 ? 0 : maximumBound;
        }

        // Triggers an input event to update the “Register” button accessibility
        inputComponent.dispatchEvent(new Event("input"))
    }
}

registry
    .category("public.interactions")
    .add("website_event.ticket_details", TicketDetails);
