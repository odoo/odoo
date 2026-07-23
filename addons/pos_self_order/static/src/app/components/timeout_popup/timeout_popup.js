import { Component, onMounted, onWillUnmount, proxy, t, useProps } from "@odoo/owl";

export class TimeoutPopup extends Component {
    static template = "pos_self_order.TimeoutPopup";
    props = useProps({
        close: t.function(),
        onTimeout: t.function(),
    });
    setup() {
        this.state = proxy({ time: 10 });

        onMounted(() => {
            this.interval = setInterval(() => {
                this.state.time -= 1;
                if (this.state.time === 0) {
                    this.props.close();
                    this.props.onTimeout();
                }
            }, 1000);
        });
        onWillUnmount(() => {
            clearInterval(this.interval);
        });
    }
}
