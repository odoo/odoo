/** @odoo-module **/
//patch the class ChatterContainer to added the click function
import { patch } from "@web/core/utils/patch";
import { ChatterContainer } from "@mail/components/chatter_container/chatter_container";
const { useRef } = owl;
patch(ChatterContainer.prototype, '@mail/components/chatter_container/chatter_container,ord-patch', {

    setup() {
        this._super();
        this.root = useRef("root")
    },
    _onClickSendMessage(ev) {// Click function of SendMessage button
        this.root.el.querySelector('#chatter_message').classList.remove("d-none");
        this.root.el.querySelector('.view').classList.remove("d-none");
        this.root.el.querySelector('.cross').classList.remove("d-none");
        this.root.el.querySelector('.o_ChatterTopbar_rightSection').classList.remove("d-none");
        this.root.el.querySelector('#send_message').classList.add("d-none");
        this.root.el.querySelector('#log_note').classList.add("d-none");
        this.root.el.querySelector('#active').classList.add("d-none");
    },
    _onClickLogNote(ev) {//Click function for LogNote button
        this.root.el.querySelector('#chatter_note').classList.remove("d-none");
        this.root.el.querySelector('.view').classList.remove("d-none");
        this.root.el.querySelector('.cross').classList.remove("d-none");
        this.root.el.querySelector('.o_ChatterTopbar_rightSection').classList.remove("d-none");
        this.root.el.querySelector('#send_message').classList.add("d-none");
        this.root.el.querySelector('#log_note').classList.add("d-none");
        this.root.el.querySelector('#active').classList.add("d-none");
    },
    _onClickActive(ev) {//Click function for Active button
        this.root.el.querySelector('#chatter_activity').classList.remove("d-none");
        this.root.el.querySelector('.view').classList.remove("d-none");
        this.root.el.querySelector('.cross').classList.remove("d-none");
        this.root.el.querySelector('.o_ChatterTopbar_rightSection').classList.remove("d-none");
        this.root.el.querySelector('#send_message').classList.add("d-none");
        this.root.el.querySelector('#log_note').classList.add("d-none");
        this.root.el.querySelector('#active').classList.add("d-none");
    },
    _onClickCross(ev) {//Click function to close chatter
        this.root.el.querySelector('#chatter_activity').classList.add("d-none");
        this.root.el.querySelector('#chatter_note').classList.add("d-none");
        this.root.el.querySelector('#chatter_message').classList.add("d-none");
        this.root.el.querySelector('.view').classList.add("d-none");
        this.root.el.querySelector('.o_ChatterTopbar_rightSection').classList.add("d-none");
        this.root.el.querySelector('.cross').classList.add("d-none");
        this.root.el.querySelector('#send_message').classList.remove("d-none");
        this.root.el.querySelector('#log_note').classList.remove("d-none");
        this.root.el.querySelector('#active').classList.remove("d-none");
        if(this.root.el.querySelector('.chat')){
            this.root.el.querySelector('.chat').classList.add("d-none");
        }
    },
});