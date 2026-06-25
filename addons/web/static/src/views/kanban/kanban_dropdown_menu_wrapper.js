import { useRef } from "@web/owl2/utils";
import { Component, onMounted, onPatched } from "@odoo/owl";
import { useDropdownCloser } from "@web/core/dropdown/dropdown_hooks";

export class KanbanDropdownMenuWrapper extends Component {
    static template = "web.KanbanDropdownMenuWrapper";
    static props = {
        slots: Object,
    };

    setup() {
        this.dropdownControl = useDropdownCloser();
        this.rootRef = useRef("rootRef");
        const applyNavigable = () => {
            const dropdownEls = this.rootRef.el.querySelectorAll(".dropdown-item");
            dropdownEls.forEach((el) => el.classList.add("o-navigable"));
        };
        onMounted(applyNavigable);
        onPatched(applyNavigable);
    }

    onClick(ev) {
        this.dropdownControl.closeAll();
    }
}
