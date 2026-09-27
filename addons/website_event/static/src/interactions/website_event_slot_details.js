import { deserializeDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

const { DateTime } = luxon;

const MAX_DATES_PER_PAGE = 6;

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
            "t-att-disabled": () => !this.selectedSlotId || this.buttonDisabled,
        },
        "li.page-item": {
            "t-on-click.prevent.stop": this._onChangePageClick,
        },
        ".o_wevent_slot_btn": {
            "t-on-click.prevent.stop": this._onSlotSelected,
            "t-att-class": (el) => ({
                "btn-light": el.dataset.slotId !== this.selectedSlotId,
                "btn-primary": el.dataset.slotId === this.selectedSlotId,
            })
        },
        ".o_wevent_slot_btn_cancel, .btn-close": {
            "t-on-click": this._onClose,
        },
        ".o_wevent_selected_slot" : {
            "t-out": () => this.selectedSlotDatetime,
        },
        ".o_wevent_selected_slot_title": {
            "t-out": () => this.selectedSlotId ? _t("Selected Date:") : _t("Select a Date:"),
        },
    };

    setup() {
        this.currentSlotPage = 0;
        this.form = this.el.querySelector("#slot_registration_form");
        this.selectedSlotDatetime = "";
        // Init first slot page
        if (this.el.querySelector(".pagination")) {
            this._changePage(0);
        }
    }

    get selectedSlotId() {
        return this.form.getAttribute("data-selected-slot-id");
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Update the displayed slots page.
     * @param {MouseEvent} ev
     */
    _onChangePageClick(ev) {
        const numPage = ev.currentTarget.classList.contains("o_wevent_slot_next") ? this.currentSlotPage + 1 : this.currentSlotPage - 1;
        const maxNumPage = Math.ceil(this.el.querySelectorAll(".o_wevent_slot_date").length / MAX_DATES_PER_PAGE) - 1;
        if (numPage < 0 || numPage > maxNumPage) {
            return;
        }
        this._changePage(numPage);
    }

    /**
     * Reset slot selection and pagination
     * @param {MouseEvent} ev
     */
    _onClose(ev) {
        this.form.removeAttribute("data-selected-slot-id");
        this.selectedSlotDatetime = "";
        this._changePage(0);
    }

    /**
     * Select a slot
     * @param {MouseEvent} ev
     */
    _onSlotSelected(ev) {
        const dataset = ev.currentTarget.dataset;
        this.selectedSlotDatetime =
            deserializeDateTime(dataset.slotStart, {tz: dataset.eventTz}).toLocaleString(DateTime.DATETIME_MED_WITH_WEEKDAY) +
            " - " + deserializeDateTime(dataset.slotEnd, {tz: dataset.eventTz}).toLocaleString(DateTime.TIME_SIMPLE);
        this.form.setAttribute("data-selected-slot-id", parseInt(ev.currentTarget.dataset.slotId));
    }

    /**
     * @param {MouseEvent} ev
     */
    async _onSubmitClick(ev) {
        const formEl = ev.currentTarget.closest("form");
        this.buttonDisabled = true;
        const modal = await this.waitFor(rpc(
            formEl.action.replace("slot_id", this.selectedSlotId),
        ));
        const modalEl = new DOMParser().parseFromString(modal, "text/html").body.firstChild;
        this.insert(modalEl, document.body);
    }

    //--------------------------------------------------------------------------
    // Methods
    //--------------------------------------------------------------------------

    /**
     * Display the specified slot page. Index starting at 0.
     * @param {Integer} numPage
     */
    _changePage(numPage) {
        this.currentSlotPage = numPage;
        const dates = this.el.querySelectorAll(".o_wevent_slot_date");
        dates.forEach((date) => date.classList.add("d-none"));
        const min = MAX_DATES_PER_PAGE * this.currentSlotPage;
        const max = MAX_DATES_PER_PAGE * (this.currentSlotPage + 1);
        Array.from(dates).slice(min, max).forEach(
            date => date.classList.remove("d-none")
        );
        // Handle previous/next buttons display
        const previousBtn = this.el.querySelector(".o_wevent_slot_previous button");
        const nextBtn = this.el.querySelector(".o_wevent_slot_next button");
        if (dates.length <= MAX_DATES_PER_PAGE) {
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
}

registry
    .category("public.interactions")
    .add("website_event.slot_details", SlotDetails);
