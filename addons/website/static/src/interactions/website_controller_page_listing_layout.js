import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";
import { rpc } from "@web/core/network/rpc";

export class WebsiteControllerPageListingLayout extends Interaction {
    static selector = ".o_website_listing_layout";
    dynamicContent = {
        ".listing_layout_switcher input": {
            "t-on-change": this.onApplyLayoutChange,
        },
        ".o_website_grid, .o_website_list": {
            "t-att-class": () => ({
                "o_website_list": this.isList,
                "o_website_grid": !this.isList,
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
    }

    /**
     * @param {Event} ev
     */
    async onApplyLayoutChange(ev) {
        const clickedValue = ev.target.value;
        this.isList = clickedValue === "list";
        await this.waitFor(rpc("/website/save_session_layout_mode", {
            layout_mode: this.isList ? "list" : "grid",
            view_id: document
                .querySelector(".listing_layout_switcher")
                .dataset.viewId,
        }));

        const activeClasses = ev.target.parentElement.dataset.activeClasses.split(" ");
        ev.target.parentElement.querySelectorAll(".btn").forEach((btn) => {
            activeClasses.map((c) => btn.classList.toggle(c));
        });
    }
}

registry
    .category("public.interactions")
    .add("website.website_controller_page_listing_layout", WebsiteControllerPageListingLayout);
