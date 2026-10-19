import { Component, onMounted, onPatched, signal, t, useProps } from "@odoo/owl";
import { useDropdownCloser } from "@web/core/dropdown/dropdown_hooks";

export class KanbanDropdownMenuWrapper extends Component {
    static template = "web.KanbanDropdownMenuWrapper";
    props = useProps({
        slots: t.object(),
    });

    rootRef = signal.ref();

    setup() {
        this.dropdownControl = useDropdownCloser();
        const applyNavigable = () => {
            const dropdownEls = this.rootRef().querySelectorAll(".dropdown-item");
            dropdownEls.forEach((el) => el.classList.add("o-navigable"));
        };
        onMounted(applyNavigable);
        onPatched(applyNavigable);
    }

    onClick(ev) {
        this.dropdownControl.closeAll();
    }
}
