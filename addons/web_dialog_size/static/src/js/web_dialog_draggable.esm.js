/** @odoo-module **/

import {ActionDialog} from "@web/webclient/actions/action_dialog";
import {onMounted, useExternalListener} from "@odoo/owl";
import {useListener} from "@web/core/utils/hooks";
import {LegacyComponent} from "@web/legacy/legacy_component";
import {Dialog} from "@web/core/dialog/dialog";

export class DialogDraggable extends LegacyComponent {
    setup() {
        this.element_position = {x: 0, y: 0};
        this.mouse_to_element_ratio = {x: 0, y: 0};
        const bound_onDrag = this.onDrag.bind(this);
        useListener("mousedown", "header.modal-header", (event) => {
            const y = parseInt(this.el.querySelector(".modal-content").offsetTop, 10);
            const x = parseInt(this.el.querySelector(".modal-content").offsetLeft, 10);
            this.mouse_to_element_ratio = {x: event.x - x, y: event.y - y};
            this.element_position = {
                x: event.x - this.mouse_to_element_ratio.x - x,
                y: event.y - this.mouse_to_element_ratio.y - y,
            };
            document.addEventListener("mousemove", bound_onDrag);
        });
        useExternalListener(document, "mouseup", () =>
            document.removeEventListener("mousemove", bound_onDrag)
        );
        onMounted(() => {
            this.el.querySelector(".modal-content").classList.add("position-absolute");
            this.el.parentNode.classList.add("position-relative");
        });
    }

    getMovePosition({x, y}) {
        return {
            x: x - this.mouse_to_element_ratio.x - this.element_position.x,
            y: y - this.mouse_to_element_ratio.y - this.element_position.y,
        };
    }
    onDrag(event) {
        const {x, y} = this.getMovePosition(event);
        const el = this.el.querySelector(".modal-content");
        el.style.left = `${x}px`;
        el.style.top = `${y}px`;
    }
}

DialogDraggable.template = "DialogDraggable";

Dialog.components = Object.assign(Dialog.components || {}, {DialogDraggable});
Object.assign(ActionDialog.components, {DialogDraggable});
