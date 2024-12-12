import { Component, useState, useSubEnv } from "@odoo/owl";
import { useVisibilityObserver } from "../builder_helpers";
import { OptionsContainer } from "../components/OptionsContainer";
import { Mutex } from "@web/core/utils/concurrency";

export class CustomizeTab extends Component {
    static template = "html_builder.CustomizeTab";
    static components = { OptionsContainer };
    static props = {
        currentOptionsContainers: { type: Array, optional: true },
    };
    static defaultProps = {
        currentOptionsContainers: [],
    };

    setup() {
        this.state = useState({
            hasContent: true,
        });
        useVisibilityObserver("content", (hasContent) => {
            this.state.hasContent = hasContent;
        });
    }
}
