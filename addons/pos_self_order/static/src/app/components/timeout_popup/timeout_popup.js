import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";

export class TimeoutPopup extends Component {
    static template = "pos_self_order.TimeoutPopup";

    setup() {
        this.state = useState({ time: 10 });

        onMounted(() => {
            this.interval = setInterval(() => {
                this.state.time -= 1;
                if (this.state.time === 0) {
                    this.props.close();
                }
            }, 1000);
        });
        onWillUnmount(() => {
            clearInterval(this.interval);
        });
    }
}
