/** @odoo-module */

import { Component, xml } from "@odoo/owl";
import { useStories } from "../stories";

export class ComponentRenderer extends Component {
    static template = xml`
        <t t-if="stories.active.component" t-component="stories.active.parentComponent" storyProps="storyProps" changeProps.bind="changeProps"/>
    `;

    setup() {
        this.stories = useStories();
    }

    get storyProps() {
        const finalProps = {};
        for (const [propName, config] of Object.entries(this.stories.active.processedProps)) {
            finalProps[propName] = config.value;
        }
        return finalProps;
    }

    changeProps(name, value) {
        this.stories.active.processedProps[name].value = value;
    }
}
