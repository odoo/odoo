import { registry } from "@web/core/registry";
import { SearchModal } from "./search_modal";

class SearchModalEdit extends SearchModal {
    dynamicContent = {
        "_root:t-on-show.bs.modal.prevent": () => {},
    }
}

registry
    .category("website.edit_active_elements")
    .add("website.search_modal", SearchModalEdit);
