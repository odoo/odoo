/** @odoo-module **/


import { TextField } from "@web/views/fields/text/text_field";
import { registry } from "@web/core/registry";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";

const { useEffect, useRef } = owl;

export class MultilineField extends TextField {
    setup(){
        const inputRef = useRef("textarea");
        useEffect(
            (inputEl) => {
                if (inputEl) {
                    inputEl.onkeydown=this.onKeydown;
                }
            },
            () => [inputRef.el]
        );
        super.setup();
    }
    onKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        if(hotkey == "enter"){
            ev.stopImmediatePropagation();
        }
    }
}

registry.category("fields").add("multiline_widget", MultilineField);
