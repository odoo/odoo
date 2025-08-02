/** @odoo-module **/

import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";


export class PracticeTask extends Interaction {
    static selector = ".SHSApractice";

    async start() {
        window.Popover.getOrCreateInstance(this.el, {
            placement: "bottom",
            trigger: "click",
            html: true,
            content: () => `<div class="text-success fw-bold">Assets loaded successfully!</div>`,
        });
    }
}

registry.category("public.interactions").add("website_practice.task2", PracticeTask);
