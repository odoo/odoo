import { Plugin } from "../plugin";
import { registry } from "@web/core/registry";
import { DIMENSIONS } from "../hooks";

const { DESKTOP, MOBILE } = DIMENSIONS;

export class ResponsivePlugin extends Plugin {
    static id = "responsive";
    static shared = ["callWithDimensions"];
    resources = {
        on_reference_content_loaded_handlers: this.responsiveParsing.bind(this),
        on_layout_dimensions_updated_handlers: this.onLayoutDimensionsUpdated.bind(this),
    };

    responsiveParsing() {
        this.parseWithDimensions(DESKTOP);
        this.parseWithDimensions(MOBILE);
    }

    callWithDimensions(callback, dimensions) {
        const originalDimensions = this.layoutDimensions;
        if (this.layoutDimensions !== dimensions) {
            this.config.updateLayoutDimensions(dimensions);
        }
        callback(dimensions);
        if (this.layoutDimensions !== originalDimensions) {
            this.config.updateLayoutDimensions(originalDimensions);
        }
    }

    parseWithDimensions(dimensions) {
        this.callWithDimensions(() => {
            // TODO EGGMAIL: should we loop over every node and trigger an event
            // on a node level, or should we allow plugins to parse the reference
            // independently (which prevents parallelization of measurements on the same element),
            // but require more complex logic to determine if a measurement has to be done in
            // the first place? Currently letting every plugin loop over the reference as they see
            // fit, to refactor if needed.
            this.trigger("on_parse_layout_with_dimensions_handlers", { dimensions });
        }, dimensions);
    }

    onLayoutDimensionsUpdated(layoutDimensions) {
        this.layoutDimensions = layoutDimensions;
    }
}

registry.category("mail-html-conversion-core-plugins").add(ResponsivePlugin.id, ResponsivePlugin);
