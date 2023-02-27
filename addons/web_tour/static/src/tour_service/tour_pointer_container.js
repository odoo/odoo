/** @odoo-module **/

import { Component, xml } from "@odoo/owl";

export class TourPointerContainer extends Component {}
TourPointerContainer.props = { pointers: Object };
TourPointerContainer.template = xml`
    <t t-foreach="Object.values(props.pointers)" t-as="pointer" t-key="pointer.id">
        <t t-component="pointer.component" t-props="pointer.props"/>
    </t>
`;
