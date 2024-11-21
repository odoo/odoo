import { Chatter } from "@mail/chatter/web_portal/chatter";

import { patch } from "@web/core/utils/patch";
import { useRef, onWillPatch, useEffect } from "@odoo/owl";

patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);
        this.topRef = useRef("top");
        onWillPatch(() => {
            // Keep the composer position under the page header on scrolling
            if (!this.props.twoColumns) {
                const paddingTop = document.querySelector("#wrapwrap header")
                    ? document.querySelector("#wrapwrap header").getBoundingClientRect().height +
                      15 +
                      "px"
                    : "";
                this.observer = new window.IntersectionObserver(
                    ([e]) =>
                        (e.target.style.paddingTop =
                            e.target.getBoundingClientRect().y < 1 ? paddingTop : "20px"),
                    {
                        threshold: [1],
                    }
                );
            }
        });
        useEffect(
            () => {
                if (this.topRef.el) {
                    this.observer?.observe(this.topRef.el);
                }
            },
            () => [this.topRef.el]
        );
    },
});
