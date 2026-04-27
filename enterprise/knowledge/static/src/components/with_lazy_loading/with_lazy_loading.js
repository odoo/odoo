import { Component, onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";
import { setIntersectionObserver } from "@knowledge/js/knowledge_utils";

export class WithLazyLoading extends Component {
    static template = "knowledge.WithLazyLoading";
    static props = {
        slots: { type: Object },
    };

    setup() {
        this.loader = useRef("loader");
        this.state = useState({ isLoaded: false });

        onMounted(() => {
            const { el } = this.loader;
            this.observer = setIntersectionObserver(el, () => {
                this.state.isLoaded = true;
            });
        });

        onWillUnmount(() => {
            this.observer.disconnect();
        });
    }
}
