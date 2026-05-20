/** @odoo-module */

import { Component, props, types as t, xml } from "@odoo/owl";
import { Tag } from "../core/tag";
import { HootLink } from "./hoot_link";

export class HootTagButton extends Component {
    static components = { HootLink };
    static template = xml`
        <t t-if="this.props.inert">
            <span
                class="rounded-full px-2"
                t-att-style="this.style"
                t-att-title="this.title"
            >
                <small class="text-xs font-bold" t-out="this.props.tag.name" />
            </span>
        </t>
        <t t-else="">
            <HootLink
                ids="{ tag: this.props.tag.name }"
                class="'rounded-full px-2'"
                style="this.style"
                title="this.title"
            >
                <small class="text-xs font-bold hidden md:inline" t-out="this.props.tag.name" />
                <span class="md:hidden">&#8205;</span>
            </HootLink>
        </t>
    `;

    // Props & plugins
    props = props({
        "inert?": t.boolean(),
        tag: t.instanceOf(Tag),
    });

    get style() {
        return `background-color: ${this.props.tag.color[0]}; color: ${this.props.tag.color[1]};`;
    }

    get title() {
        return `Tag ${this.props.tag.name}`;
    }
}
