/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useStories } from "../../stories";
import { ObjectRenderer } from "../../components/object_renderer/object_renderer";

export class Events extends Component {
    static template = "pos_owlybook.events";
    static components = { ObjectRenderer };

    setup() {
        this.stories = useStories();
    }

    /**
     * The goal of this function is to get events of the active stories, if there is not return empty dic
     * @returns {*|{}}
     */
    get storyEvents() {
        return this.stories.active?.events || {};
    }
}
