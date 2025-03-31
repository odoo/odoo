/** @odoo-module */

import { Component, xml } from "@odoo/owl";
import { Tag } from "../core/tag";
import { HootLink } from "./hoot_link";

/**
 * @typedef {{
 *  inert?: boolean;
 *  tag: Tag;
 * }} HootTagButtonProps
 */

/** @extends {Component<HootTagButtonProps, import("../hoot").Environment>} */
export class HootTagButton extends Component {
    static components = { HootLink };

    static props = {
        inert: { type: Boolean, optional: true },
        tag: Tag,
    };

    static template = xml`
        <t t-if="props.inert">
            <span
                class="rounded-full px-2"
                t-att-style="style"
                t-att-title="title"
            >
                <small class="text-xs font-bold" t-esc="props.tag.name" />
            </span>
        </t>
        <t t-else="">
            <HootLink
                type="'tag'"
                id="props.tag.name"
                class="'rounded-full px-2'"
                style="style"
                title="title"
            >
                <small class="text-xs font-bold hidden md:inline" t-esc="props.tag.name" />
                <span class="md:hidden">&#8205;</span>
            </HootLink>
        </t>
    `;

    get style() {
        return `background-color: ${this.props.tag.color[0]}; color: ${this.props.tag.color[1]};`;
    }

    get title() {
        return `Tag ${this.props.tag.name}`;
    }
}
