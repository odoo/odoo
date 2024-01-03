/** @odoo-module */

import { Component, xml } from "@odoo/owl";
import { Tag } from "../core/tag";
import { withParams } from "../core/url";

/**
 * @typedef {{
 *  disabled?: boolean;
 *  tag: Tag;
 * }} HootTagButtonProps
 */

/** @extends Component<HootTagButtonProps, import("../hoot").Environment> */
export class HootTagButton extends Component {
    static props = {
        disabled: { type: Boolean, optional: true },
        tag: Tag,
    };

    static template = xml`
        <a
            t-att="{ href: !props.disabled and withParams('tag', props.tag.name) }"
            class="hoot-tag badge rounded-pill px-2 text-decoration-none"
            t-attf-style="--hoot-tag-bg: {{ props.tag.color[0] }}; --hoot-tag-text: {{ props.tag.color[1] }};"
            t-attf-title='"{{ props.tag.name }}" tag'
        >
            <strong class="d-none d-md-inline" t-esc="props.tag.name" />
            <span class="d-md-none">&#8205;</span>
        </a>
    `;

    withParams = withParams;
}
