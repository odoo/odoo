/** @odoo-module **/
import {registry} from "@web/core/registry";
//Used to add widget to view the recorded video in the form view
const {Component, useRef, onMounted} = owl;

export class VideoWidget extends Component {
    static template = 'VideoWidget'
    setup() {
        onMounted(this.mount);
        super.setup();
    }
    mount() {
        $('source').attr('src', this.props.value);
    }
}
registry.category("fields").add("videoWidget", VideoWidget);