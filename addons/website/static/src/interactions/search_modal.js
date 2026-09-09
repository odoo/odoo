/** @odoo-module native */
import { makeLogger } from "@web/core/debug/debug_logger";
import { registry } from "@web/core/registry";
import { Modal } from "@web/libs/bootstrap";
import { Interaction } from "@web/public/interaction";

const log = makeLogger("website.interaction.search_modal");

export class SearchModal extends Interaction {
    static selector = "#o_search_modal_block #o_search_modal";
    dynamicContent = {
        _root: {
            "t-on-shown.bs.modal": () => this.el.querySelector(".search-query").focus(),
        },
    };
    destroy() {
        log.lifecycle("SearchModal destroy: dispose modal", () => ({
            hasInstance: !!Modal.getInstance(this.el),
        }));
        Modal.getInstance(this.el)?.dispose();
    }
}

registry.category("public.interactions").add("website.search_modal", SearchModal);
