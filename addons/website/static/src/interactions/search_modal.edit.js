import { registry } from "@web/core/registry";
import { SearchModal } from "./search_modal";

const SearchModalEdit = I => class extends I {
    dynamicContent = {
        "_root": {
            "t-on-show.bs.modal.prevent": () => {}
        },
    }
};

registry
    .category("website.editable_active_elements_builders")
    .add("website.search_modal", {
        Interaction: SearchModal,
        mixin: SearchModalEdit,
    });