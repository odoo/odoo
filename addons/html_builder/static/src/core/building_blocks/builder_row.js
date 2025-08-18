import { Component, onMounted, useRef, useState } from "@odoo/owl";
import {
    useVisibilityObserver,
    useApplyVisibility,
    basicContainerBuilderComponentProps,
    useBuilderComponent,
} from "../utils";
import { BuilderComponent } from "./builder_component";
import { uniqueId } from "@web/core/utils/functions";

export class BuilderRow extends Component {
    static template = "html_builder.BuilderRow";
    static components = { BuilderComponent };
    static props = {
        ...basicContainerBuilderComponentProps,
        label: { type: String, optional: true },
        tooltip: { type: String, optional: true },
        slots: { type: Object, optional: true },
        level: { type: Number, optional: true },
        expand: { type: Boolean, optional: true },
    };
    static defaultProps = { expand: false };

    setup() {
        useBuilderComponent();
        useVisibilityObserver("content", useApplyVisibility("root"));

        this.state = useState({
            expanded: this.props.expand,
            tooltip: this.props.tooltip,
        });

        if (this.props.slots.collapse) {
            useVisibilityObserver("collapse-content", useApplyVisibility("collapse"));

            this.collapseContentId = uniqueId("builder_collapse_content_");
        }

        this.labelRef = useRef("label");
        onMounted(() => {
            const labelEl = this.labelRef.el;
            if (!this.state.tooltip && labelEl && labelEl.clientWidth < labelEl.scrollWidth) {
                this.state.tooltip = this.props.label;
            }
        });
    }

    getLevelClass() {
        return this.props.level ? `hb-row-sublevel hb-row-sublevel-${this.props.level}` : "";
    }

    toggleCollapseContent() {
        this.state.expanded = !this.state.expanded;
    }
}
