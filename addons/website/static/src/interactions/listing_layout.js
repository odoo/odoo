/** @odoo-module native */
import { makeLogger } from "@web/core/debug/debug_logger";
import { rpc } from "@web/core/network";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

const log = makeLogger("website.interaction.listing_layout");

export class ListingLayout extends Interaction {
    static selector = ".o_website_listing_layout";
    dynamicContent = {
        ".listing_layout_switcher input": {
            "t-on-change": this.onApplyLayoutChange,
        },
        ".o_website_grid, .o_website_list": {
            "t-att-class": () => ({
                o_website_list: this.isList,
                o_website_grid: !this.isList,
            }),
        },
        ".o_website_grid > div, .o_website_list > div": {
            "t-att-class": () => ({
                "col-lg-3 col-md-4 col-sm-6 px-2 col-xs-12": !this.isList,
            }),
        },
    };

    setup() {
        this.isList = this.el.querySelector(".o_website_list") != null;
        log.lifecycle("ListingLayout setup", () => ({ isList: this.isList }));
    }

    /**
     * @param {Event} ev
     */
    async onApplyLayoutChange(ev) {
        const clickedValue = ev.target.value;
        this.isList = clickedValue === "list";
        log.logic("ListingLayout onApplyLayoutChange", () => ({ clickedValue }));
        const endSave = log.perf("ListingLayout save session layout mode");
        await this.waitFor(
            rpc("/website/save_session_layout_mode", {
                layout_mode: this.isList ? "list" : "grid",
                view_id: this.el.querySelector(".listing_layout_switcher").dataset
                    .viewId,
            }),
        );
        endSave(() => ({ isList: this.isList }));

        const activeClasses = ev.target.parentElement.dataset.activeClasses.split(" ");
        ev.target.parentElement.querySelectorAll(".btn").forEach((btn) => {
            activeClasses.map((c) => btn.classList.toggle(c));
        });
    }
}

registry.category("public.interactions").add("website.listing_layout", ListingLayout);
