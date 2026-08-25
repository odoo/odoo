/** @odoo-module **/

import { Component, onMounted, onWillUnmount, proxy } from "@odoo/owl";

import { 
    countSMS, 
    extractSmsEncoding, 
    GSM7_MAX_CHAR, 
    UCS2_MAX_CHAR 
} from "@sms/core/sms_char_counter_utils";
import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";


export class SmsCharCounter extends Component {
    static template = "sms.SmsCharCounter";
        static props = {
            ...standardWidgetProps,
        };
    
        setup() {
            this.state = proxy({ value: "" });
    
            onMounted(() => {
                const textarea = document.querySelector(".o_field_widget[name='body'] textarea, .o_field_widget[name='body'] input");
                if (textarea) {
                    this._onInputHandler = (ev) => {
                        this.state.value = ev.target.value;
                    };
                    textarea.addEventListener("input", this._onInputHandler);
                    this.state.value = textarea.value || "";
                }
            });
    
            onWillUnmount(() => {
                const textarea = document.querySelector(".o_field_widget[name='body'] textarea, .o_field_widget[name='body'] input");
                if (textarea && this._onInputHandler) {
                    textarea.removeEventListener("input", this._onInputHandler);
                }
            });
        }
    
        get nbrChar() {
            const val = this.state.value;
            return val.length + (val.match(/\n/g) || []).length;
        }
    
        get nbrCharExplanation() {
            return "";
        }
    
        get encoding() {
            return extractSmsEncoding(this.state.value);
        }
    
        get nbrSMS() {
            return countSMS(this.nbrChar, this.encoding);
        }
    
        get maxChar() {
            return this.encoding === "UNICODE" ? UCS2_MAX_CHAR : GSM7_MAX_CHAR;
        }
}

registry.category("view_widgets").add("sms_char_counter", {
    component: SmsCharCounter,
});
