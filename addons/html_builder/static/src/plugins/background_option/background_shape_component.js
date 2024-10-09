import { defaultBuilderComponents } from "@html_builder/core/default_builder_components";
import { Component, useRef } from "@odoo/owl";

export class BackgroundShapeComponent extends Component {
    static template = "html_builder.BackgroundShapeComponent";
    static components = {
        ...defaultBuilderComponents,
    };
    static props = {
        getShapeStyleUrl: { type: Function },
        shapesInfo: { type: Object },
    };

    setup() {
        this.basicRef = useRef("basic");
        this.linearRef = useRef("linear");
        this.creativeRef = useRef("creative");
        this.basicShapes = [
            { name: "Connections", shapes: this.props.shapesInfo.connectionShapes },
            { name: "Origins", shapes: this.props.shapesInfo.originShapes },
            { name: "Bold", shapes: this.props.shapesInfo.boldShapes },
            { name: "Blobs", shapes: this.props.shapesInfo.blobShapes },
        ];
        this.linearShapes = [
            { name: "Airy & Zigs", shapes: this.props.shapesInfo.airyAndZigShapes },
        ];
        this.creativeShapes = [
            { name: "Wavy", shapes: this.props.shapesInfo.wavyShapes },
            { name: "Block & Rainy", shapes: this.props.shapesInfo.blockAndRainyShapes },
            { name: "Floating Shape", shapes: this.props.shapesInfo.floatingShapes },
        ];
    }
    closeComponent() {
        this.env.closeCustomizeComponent();
    }
    scrollToShapes(sectionName) {
        const sectionsToElementsMap = {
            basic: this.basicRef.el,
            linear: this.linearRef.el,
            creative: this.creativeRef.el,
        };
        sectionsToElementsMap[sectionName].scrollIntoView({ behavior: "smooth", block: "start" });
    }
}
