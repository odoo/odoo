import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

export class WebsiteEventTrack extends Interaction {
    static selector = ".o_wevent_event";

    dynamicContent = {
        _window: {
            "t-on-scroll": () => this.updateAgendaScroll(),
            "t-on-resize": () => this.updateAgendaScroll(),
        },
        "#event_track_search": { "t-on-input.prevent": (ev) => {
            this.searchText = ev.currentTarget.value.toLowerCase();
        }},
        ".o_we_online_agenda": { "t-on-scroll": this.onAgendaScroll },
        ".event_track": { "t-att-class": (el) => ({ "invisible": !el.textContent.toLowerCase().includes(this.searchText) }) },
        "#search_summary": { "t-att-class": () => ({ "invisible": !this.searchText }) },
        "#search_number": { "t-out": () => this.tracks.filter(element => !element.classList.contains('invisible')).length },
        ".o_we_agenda_horizontal_scroller_container": {
            "t-on-scroll": this.alignAgendaScroll,
            "t-att-class": () => ({
                "d-none": !(this.visibleAgenda && this.visibleAgenda.classList.contains("o_we_online_agenda_has_scroll")),
            }),
        },
        ".o_we_agenda_horizontal_scroller": { "t-att-style": () => ({ "width": this.computeScrollerWidth() }) },
        ".o_we_agenda_card_filter_badges .o_badge_clickable": {
            "t-on-click": this.onBadgeFilterClick,
        },
    };

    setup() {
        this.el.querySelectorAll("[data-bs-toggle='popover']").forEach((el) => {
            const bsPopover = window.Popover.getOrCreateInstance(el);
            this.registerCleanup(() => bsPopover.dispose());
        });

        this.searchText = "";
        this.agendaScroller = this.el.querySelector(".o_we_agenda_horizontal_scroller_container");
        this.agendaScrollerElement = this.agendaScroller?.querySelector(".o_we_agenda_horizontal_scroller");
        this.agendas = Array.from(this.el.querySelectorAll(".o_we_online_agenda"));
        this.tracks = Array.from(this.el.querySelectorAll(".event_track"));

        if (this.agendas.length > 0) {
            this.checkAgendasOverflow(this.agendas);
        }

        if (this.agendaScroller) {
            this.updateAgendaScroll = this.debounced(this.updateAgendaScroll, 50);
            this.updateAgendaScroll();
        }
    }

    alignAgendaScroll() {
        if (this.visibleAgenda && this.agendaScroller) {
            this.visibleAgenda.scrollLeft = this.agendaScroller.scrollLeft;
        }
    }

    /**
     * Dynamic horizontal scrollbar.
     * It's meant the show up as a sticky scrollbar at the bottom of the screen, to allow scrolling
     * the agenda horizontally even if you've not reached the bottom of the agenda container.
     * Makes the user experience much smoother.
     *
     * Technically, the code checks "what is the last agenda on the screen" and enables our sticky
     * scrollbar based on that.
     */
    updateAgendaScroll() {
        if (!this.agendaScroller) {
            return ;
        }

        // reverse the agendas, we always want the last agenda "on screen" to be the scrolled one
        this.visibleAgenda = this.agendas.toReversed().find((el) => {
            const rect = el.getBoundingClientRect();
            const containerOffset = {
                top: rect.top + window.scrollY + 30,  // some offset for a better experience
                bottom: rect.bottom + window.scrollY
            };
            const windowOffset = {
                top: window.scrollY,
                bottom: window.scrollY + window.innerHeight
            };

            // if the top of the container if visible but NOT the bottom
            return (containerOffset.top < windowOffset.bottom) &&
                !(containerOffset.bottom < windowOffset.bottom);
        });
        if (this.visibleAgenda) {
            requestAnimationFrame(() => {
                this.agendaScroller.scrollLeft = this.visibleAgenda.scrollLeft;
            });
        }
    }

    /**
     * @param {Object} agendas
     */
    checkAgendasOverflow(agendas) {
        agendas.forEach(agendaEl => {
            const hasScroll = agendaEl.querySelector("table").clientWidth > agendaEl.clientWidth;

            agendaEl.classList.toggle("o_we_online_agenda_has_scroll", hasScroll);
            agendaEl.classList.toggle("o_we_online_agenda_has_content_hidden", hasScroll);
        });
    }

    /**
     * @param {Event} event
     */
    onAgendaScroll(event) {
        const currentTarget = event.currentTarget;
        const tableEl = currentTarget.querySelector("table");
        const gutter = 4; // = map-get($spacers, 1)
        const gap = tableEl.clientWidth - currentTarget.clientWidth - gutter;

        currentTarget.classList.add("o_we_online_agenda_is_scrolling");
        currentTarget.classList.toggle("o_we_online_agenda_has_content_hidden", gap > Math.ceil(currentTarget.scrollLeft));

        requestAnimationFrame(() => {
            setTimeout(() => {
                currentTarget.classList.remove("o_we_online_agenda_is_scrolling");
            }, 200);
        });

        if (this.agendaScroller && this.visibleAgenda) {
            this.agendaScroller.scrollLeft = this.visibleAgenda.scrollLeft;
        }
    }

    computeScrollerWidth() {
        if (this.visibleAgenda && this.visibleAgenda.classList.contains("o_we_online_agenda_has_scroll")) {
            // need to account for vertical scrollbar width
            const verticalScrollbarWidth = window.innerWidth - document.documentElement.clientWidth;
            return (this.visibleAgenda.scrollWidth + verticalScrollbarWidth) + "px";
        }
    }

    onBadgeFilterClick(ev) {
        const target = document.getElementById("event_track_search");
        if (target.value === ev.currentTarget.title) {
            target.value = "";
        } else {
            target.value = ev.currentTarget.title;
            target.dispatchEvent(new Event("input"));
        }
    }
}

registry
    .category("public.interactions")
    .add("website_event_track.website_event_track", WebsiteEventTrack);
