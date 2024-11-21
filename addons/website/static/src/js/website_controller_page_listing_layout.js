/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.WebsiteControllerPageListingLayout = publicWidget.Widget.extend({
    selector: ".o_website_listing_layout",
    disabledInEditableMode: true,
    events: {
        "change .listing_layout_switcher input": "_onApplyLayoutChange",
    },
    
    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onApplyLayoutChange(ev) {
        const wysiwyg = this.options.wysiwyg;
        if (wysiwyg) {
            wysiwyg.odooEditor.observerUnactive("_onApplyLayoutChange");
        }
        const clickedValue = ev.target.value;
        const isList = clickedValue === "list";
        if (!this.editableMode) {
            rpc("/website/save_session_layout_mode", {
                layout_mode: isList ? "list" : "grid",
                view_id: document
                    .querySelector(".listing_layout_switcher")
                    .getAttribute("data-view-id"),
            });
        }

        const activeClasses = ev.target.parentElement.dataset.activeClasses.split(" ");
        ev.target.parentElement.querySelectorAll(".btn").forEach((btn) => {
            activeClasses.map((c) => btn.classList.toggle(c));
        });

        const el = document.querySelector(isList ? ".o_website_grid" : ".o_website_list");
        this._toggle_view_mode(el, isList);

        if (wysiwyg) {
            wysiwyg.odooEditor.observerActive("_onApplyLayoutChange");
        }
    },

    _toggle_view_mode(el, isList) {
        if (el) {
            el.classList.toggle("o_website_list", isList);
            el.classList.toggle("o_website_grid", !isList);
            const classList = isList ? "" : "col-lg-3 col-md-4 col-sm-6 px-2 col-xs-12";
            // each card must have the correct bootstrap classes
            [...document.querySelectorAll(".o_website_list > div, .o_website_grid > div")].forEach((card) => {
                card.classList = classList;
            });
        }
    }
});
