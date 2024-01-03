/** @odoo-module */

import { Component, xml } from "@odoo/owl";
import { Tag } from "../core/tag";
import { HootLink } from "./hoot_link";

/**
 * @typedef {{
 *  disabled?: boolean;
 *  tag: Tag;
 * }} HootTagButtonProps
 */

/** @extends {Component<HootTagButtonProps, import("../hoot").Environment>} */
export class HootTagButton extends Component {
    static components = { HootLink };

    static props = {
        disabled: { type: Boolean, optional: true },
        tag: Tag,
    };

    static template = xml`
        <HootLink
            type="'tag'"
            id="props.tag.name"
            disabled="props.disabled"
            class="'rounded-full px-2'"
            style="'background-color: ' + props.tag.color[0] + '; color: ' + props.tag.color[1] + ';'"
            title="'Tag ' +  props.tag.name"
        >
            <small class="text-xs font-bold hidden md:inline" t-esc="props.tag.name" />
            <span class="md:hidden">&#8205;</span>
        </HootLink>
    `;
}
