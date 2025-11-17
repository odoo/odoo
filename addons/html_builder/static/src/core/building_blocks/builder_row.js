import { Component, useRef, useState } from "@odoo/owl";
import { uniqueId } from "@web/core/utils/functions";
import { useService } from "@web/core/utils/hooks";
import {
    basicContainerBuilderComponentProps,
    useApplyVisibility,
    useBuilderComponent,
    useVisibilityObserver,
} from "../utils";
import { BuilderComponent } from "./builder_component";

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
        extraLabelClass: { type: String, optional: true },
        observeCollapseContent: { type: Boolean, optional: true },
        fullRowToggler: { type: Boolean, optional: true },
    };
    static defaultProps = { expand: false, observeCollapseContent: false, fullRowToggler: false };

    setup() {
        useBuilderComponent();
        useVisibilityObserver("content", useApplyVisibility("root"));

        this.state = useState({
            expanded: this.props.expand,
        });
        this.hasTooltip = this.props.tooltip ? true : undefined;

        if (this.props.slots.collapse) {
            useVisibilityObserver("collapse-content", useApplyVisibility("collapse"));

            this.collapseContentId = uniqueId("builder_collapse_content_");
        }

        this.labelRef = useRef("label");
        this.tooltip = useService("tooltip");
    }

    getLevelClass() {
        return this.props.level ? `hb-row-sublevel hb-row-sublevel-${this.props.level}` : "";
    }

    onRowContentClick() {
        if (this.props.fullRowToggler) {
            this.toggleCollapseContent();
        }
    }

    toggleCollapseContent() {
        this.state.expanded = !this.state.expanded;
    }

    openTooltip() {
        if (this.hasTooltip === undefined) {
            const labelEl = this.labelRef.el;
            this.hasTooltip = labelEl && labelEl.clientWidth < labelEl.scrollWidth;
        }
        if (this.hasTooltip) {
            const tooltip = this.props.tooltip || this.props.label;
            this.removeTooltip = this.tooltip.add(this.labelRef.el, { tooltip });
        }
    }

    closeTooltip() {
        if (this.removeTooltip) {
            this.removeTooltip();
        }
    }

    get displayCollapseContent() {
        return (
            !!this.props.slots.collapse &&
            (this.props.observeCollapseContent || this.state.expanded)
        );
    }
}
