import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

const { DateTime } = luxon;

export class SlotDetails extends Interaction {
    static selector = ".o_wevent_js_slot_details";
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _envBus: () => this.env.bus,
    };
    dynamicContent = {
        _envBus: {
            "t-on-websiteEvent.enableSubmit": () => this.buttonDisabled = false,
        },
        ".a-submit": {
            "t-on-click.prevent.stop": this._onSubmitClick,
            "t-att-disabled": () => !this.selectedSlot || this.buttonDisabled ? "disabled" : false,
        },
        "li.page-item": {
            "t-on-click.prevent.stop": this._onNextPageClick,
        },
        ".o_wevent_slot_btn": {
            "t-on-click.prevent.stop": this._onSlotSelected,
        },
    };

    get selectedSlot() {
        return this.form.getAttribute("data-selected-slot-id");
    }

    setup() {
        this.currentSlotPage = 0;
        this.datesLimitPerPage = 8;
        this.form = this.el.querySelector("#slot_registration_form");
        this.selectedSlotDatetime = this.el.querySelector(".o_wevent_selected_slot");
        this.selectedSlotTitle = this.el.querySelector(".o_wevent_selected_slot_title");
        // Init first slot page
        if (this.el.querySelector(".pagination")) {
            this._changePage(0);
        }
    }

    /**
     * Display the specified slot page. Index starting at 0.
     * @param {Integer} numPage
     */
    _changePage(numPage) {
        const dates = this.el.querySelectorAll(".o_wevent_slot_date");
        this.currentSlotPage = numPage;
        dates.forEach((date) => date.classList.add("d-none"));
        const min = this.datesLimitPerPage * this.currentSlotPage;
        const max = this.datesLimitPerPage * (this.currentSlotPage + 1);
        Array.from(dates).slice(min, max).forEach(
            date => date.classList.remove("d-none")
        );
        // Handle previous/next buttons display
        const previousBtn = this.el.querySelector(".o_wevent_slot_previous button");
        const nextBtn = this.el.querySelector(".o_wevent_slot_next button");
        if (dates.length <= this.datesLimitPerPage) {
            [previousBtn, nextBtn].forEach((button) => button.classList.add("d-none"));
        } else {
            [previousBtn, nextBtn].forEach((button) => {
                button.classList.remove("disabled");
            });
            if (this.currentSlotPage === 0) {
                previousBtn.classList.add("disabled");
            } else if(max >= dates.length) {
                nextBtn.classList.add("disabled");
            }
        }
    }

    /**
     * Update the displayed slots page.
     * @param {MouseEvent} ev
     */
    _onNextPageClick(ev) {
        const numPage = ev.currentTarget.classList.contains("o_wevent_slot_next") ? this.currentSlotPage + 1 : this.currentSlotPage - 1;
        this._changePage(numPage);
    }

    /**
     * Select a slot
     * @param {MouseEvent} ev
     */
    _onSlotSelected(ev) {
        // Visually select the button
        this.el.querySelectorAll(".o_wevent_slot_btn").forEach((btn) => btn.classList.replace("btn-primary", "btn-light"));
        ev.currentTarget.classList.replace("btn-light", "btn-primary");
        // Change selected slot title
        const selectedDatetime = DateTime.fromISO(ev.currentTarget.dataset.slotStart.replace(" ", "T"), { zone: "UTC" });
        const localizedDatetime = selectedDatetime.setZone(ev.currentTarget.dataset.eventTz);
        this.selectedSlotTitle.textContent = _t("Selected Date: ");
        this.selectedSlotDatetime.textContent = localizedDatetime.toFormat("MMM dd yyyy, EEEE, h:mm a");
        this.form.setAttribute("data-selected-slot-id", parseInt(ev.currentTarget.dataset.slotId));
    }

    /**
     * @param {MouseEvent} ev
     */
    async _onSubmitClick(ev) {
        const formEl = ev.currentTarget.closest("form");
        this.buttonDisabled = true;
        const modal = await this.waitFor(rpc(
            formEl.action,
            Object.assign(
                {},
                Object.fromEntries(new FormData(formEl)),
                {'selected_slot': this.selectedSlot}
            )
        ));
        const modalEl = new DOMParser().parseFromString(modal, "text/html").body.firstChild;
        this.insert(modalEl, document.body);
    }

}

registry
    .category("public.interactions")
    .add("website_event.slot_details", SlotDetails);
