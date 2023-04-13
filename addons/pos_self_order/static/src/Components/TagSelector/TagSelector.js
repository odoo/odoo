/** @odoo-module */

import { Component, useEffect, useRef } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/SelfOrderService";

export class TagSelector extends Component {
    static template = "pos_self_order.TagSelector";
    static props = ["activeTag", "tagList", "onClick"];
    setup() {
        this.selfOrder = useSelfOrder();
        this.tagButtons = Object.fromEntries(
            Array.from(this.selfOrder.tagList).map((tag) => {
                return [tag, useRef(`tag_${tag}`)];
            })
        );
        this.tagList = useRef("tagList");
        // we scroll the tag list horizontally so that the selected tag is in the middle of the screen
        useEffect(
            (activeTag) => {
                if (!activeTag) {
                    return;
                }
                const tag = this.tagButtons[activeTag].el;
                this.tagList.el.scroll({
                    left: tag.offsetLeft + tag.offsetWidth / 2 - window.innerWidth / 2,
                    behavior: "smooth",
                });
            },
            () => [this.props.activeTag]
        );
    }
}
