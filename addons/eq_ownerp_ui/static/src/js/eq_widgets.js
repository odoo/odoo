/** @odoo-module **/
import { registry } from "@web/core/registry";
import { CharField } from "@web/views/fields/char/char_field";
import { useInputField } from "@web/views/fields/input_field_hook";
import {onMounted, useRef } from "@odoo/owl";

export class EQColor extends CharField {
   static template = 'FieldEQColor';
   setup(){
       super.setup();
       this.input = useRef('eq_color_input');
       useInputField({ getValue: () => this.props.value || "", refName: "eq_color_input" });
       onMounted(this.onMounted);
   }
   onMounted() {
        var eq_color_template = $(this.input.el);
        this.input.el.value = this.props.value;
        var eq_colorpicker_input_addon = $(this.input.el).siblings('.eq_selected_color');
        eq_colorpicker_input_addon.css("background-color", this.input.el.value);
        $(eq_color_template).colorpicker({
            horizontal: true,
          }).on('changeColor', function (e) {
            eq_colorpicker_input_addon.css("background-color", e.value);
          });
    }

}
registry.category("fields").add("eq_color", EQColor);