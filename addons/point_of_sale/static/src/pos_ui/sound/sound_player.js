/** @odoo-module */

import { Component, xml } from "@odoo/owl";

export class SoundPlayer extends Component {}
SoundPlayer.template = xml`
    <t t-foreach="props.sounds" t-as="sound" t-key="sound">
        <audio t-att-src="sound_value.src" autoplay="" t-on-ended="sound_value.cleanup"/>
    </t>
`;
