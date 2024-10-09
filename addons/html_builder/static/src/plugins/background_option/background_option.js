import { useIsActiveItem } from "@html_builder/core/building_blocks/utils";
import { defaultBuilderComponents } from "@html_builder/core/default_builder_components";
import { BackgroundShapeComponent } from "@html_builder/plugins/background_option/background_shape_component";
import { applyFunDependOnSelectorAndExclude } from "@html_builder/plugins/utils";
import { Plugin } from "@html_editor/plugin";
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { BackgroundImage } from "./background_image";
import { BackgroundPosition } from "./background_position";
import { BackgroundShape } from "./background_shape";

class BackgroundOptionPlugin extends Plugin {
    static id = "BackgroundOption";
    static dependencies = ["backgroundShape"];
    resources = {
        builder_options: [
            // TODO: add the other options that need BackgroundComponent
            {
                selector: "section",
                OptionComponent: BackgroundComponent,
                props: {
                    withColors: true,
                    withImages: true,
                    // todo: handle with_videos
                    withShapes: true,
                    withGradient: true,
                    withColorCombinations: true,
                    getShapeData: this.dependencies.backgroundShape.getShapeData,
                    getShapeStyleUrl: this.dependencies.backgroundShape.getShapeStyleUrl,
                    shapesInfo: {
                        connectionShapes: this.connectionShapes,
                        originShapes: this.originShapes,
                        boldShapes: this.boldShapes,
                        blobShapes: this.blobShapes,
                        airyAndZigShapes: this.airyAndZigShapes,
                        wavyShapes: this.wavyShapes,
                        blockAndRainyShapes: this.blockAndRainyShapes,
                        floatingShapes: this.floatingShapes,
                        allPossiblesShapes: this.allPossiblesShapes,
                    },
                },
            },
        ],
        normalize_handlers: this.normalize.bind(this),
        system_classes: ["o_colored_level"],
        allPossiblesShapes: this.allPossiblesShapes,
    };
    setup() {
        this.coloredLevelBackgroundParams = [];
        for (const builderOption of this.resources.builder_options) {
            if (builderOption.props.withColors && builderOption.props.withColorCombinations) {
                this.coloredLevelBackgroundParams.push({
                    selector: builderOption.selector,
                    exclude: builderOption.exclude || "",
                });
            }
        }
    }
    get connectionShapes() {
        return [
            { shapeUrl: "web_editor/Connections/01", label: "Connections 01" },
            { shapeUrl: "web_editor/Connections/02", label: "Connections 02" },
            { shapeUrl: "web_editor/Connections/03", label: "Connections 03" },
            { shapeUrl: "web_editor/Connections/04", label: "Connections 04" },
            { shapeUrl: "web_editor/Connections/05", label: "Connections 05" },
            { shapeUrl: "web_editor/Connections/06", label: "Connections 06" },
            { shapeUrl: "web_editor/Connections/07", label: "Connections 07" },
            { shapeUrl: "web_editor/Connections/08", label: "Connections 08" },
            { shapeUrl: "web_editor/Connections/09", label: "Connections 09" },
            { shapeUrl: "web_editor/Connections/10", label: "Connections 10" },
            { shapeUrl: "web_editor/Connections/11", label: "Connections 11" },
            { shapeUrl: "web_editor/Connections/12", label: "Connections 12" },
            { shapeUrl: "web_editor/Connections/13", label: "Connections 13" },
            { shapeUrl: "web_editor/Connections/14", label: "Connections 14" },
            { shapeUrl: "web_editor/Connections/15", label: "Connections 15" },
            { shapeUrl: "web_editor/Connections/16", label: "Connections 16" },
            { shapeUrl: "web_editor/Connections/17", label: "Connections 17" },
            { shapeUrl: "web_editor/Connections/18", label: "Connections 18" },
            { shapeUrl: "web_editor/Connections/19", label: "Connections 19" },
            { shapeUrl: "web_editor/Connections/20", label: "Connections 20" },
        ];
    }
    get originShapes() {
        return [
            { shapeUrl: "web_editor/Origins/02_001", label: "Origins 01" },
            { shapeUrl: "web_editor/Origins/05", label: "Origins 02" },
            { shapeUrl: "web_editor/Origins/06_001", label: "Origins 03" },
            { shapeUrl: "web_editor/Origins/07_002", label: "Origins 04" },
            { shapeUrl: "web_editor/Origins/09_001", label: "Origins 05" },
            { shapeUrl: "web_editor/Origins/16", label: "Origins 06", animated: true },
            { shapeUrl: "web_editor/Origins/17", label: "Origins 07", animated: true },
            { shapeUrl: "web_editor/Origins/19", label: "Origins 08" },
        ];
    }
    get boldShapes() {
        return [
            { shapeUrl: "web_editor/Bold/01", label: "Bold 01", animated: true },
            { shapeUrl: "web_editor/Bold/03", label: "Bold 02" },
            { shapeUrl: "web_editor/Bold/04", label: "Bold 03" },
            { shapeUrl: "web_editor/Bold/05_001", label: "Bold 04" },
            { shapeUrl: "web_editor/Bold/06_001", label: "Bold 05" },
            { shapeUrl: "web_editor/Bold/07_001", label: "Bold 06" },
            { shapeUrl: "web_editor/Bold/08", label: "Bold 07" },
            { shapeUrl: "web_editor/Bold/09", label: "Bold 08" },
            { shapeUrl: "web_editor/Bold/10_001", label: "Bold 09" },
            { shapeUrl: "web_editor/Bold/02_001", label: "Bold 10" },
        ];
    }
    get blobShapes() {
        return [
            { shapeUrl: "web_editor/Blobs/01_001", label: "Blobs 01" },
            { shapeUrl: "web_editor/Blobs/02", label: "Blobs 02" },
            { shapeUrl: "web_editor/Blobs/03", label: "Blobs 03" },
            { shapeUrl: "web_editor/Blobs/04", label: "Blobs 04" },
            { shapeUrl: "web_editor/Blobs/05", label: "Blobs 05" },
            { shapeUrl: "web_editor/Blobs/06", label: "Blobs 06" },
            { shapeUrl: "web_editor/Blobs/07", label: "Blobs 07" },
            { shapeUrl: "web_editor/Blobs/08", label: "Blobs 08" },
            { shapeUrl: "web_editor/Blobs/09", label: "Blobs 09" },
            { shapeUrl: "web_editor/Blobs/10_001", label: "Blobs 10" },
            { shapeUrl: "web_editor/Blobs/11", label: "Blobs 11" },
            { shapeUrl: "web_editor/Blobs/12", label: "Blobs 12" },
        ];
    }
    get airyAndZigShapes() {
        return [
            { shapeUrl: "web_editor/Airy/01", label: "Airy 01" },
            { shapeUrl: "web_editor/Airy/06", label: "Airy 02" },
            { shapeUrl: "web_editor/Airy/02", label: "Airy 03" },
            { shapeUrl: "web_editor/Airy/07", label: "Airy 04" },
            { shapeUrl: "web_editor/Airy/08", label: "Airy 05" },
            { shapeUrl: "web_editor/Airy/10", label: "Airy 06" },
            { shapeUrl: "web_editor/Airy/09", label: "Airy 07" },
            { shapeUrl: "web_editor/Airy/11", label: "Airy 08" },
            { shapeUrl: "web_editor/Airy/03_001", label: "Airy 09", animated: true },
            { shapeUrl: "web_editor/Airy/04_001", label: "Airy 10", animated: true },
            { shapeUrl: "web_editor/Airy/05_001", label: "Airy 11", animated: true },
            { shapeUrl: "web_editor/Airy/12_001", label: "Airy 12", animated: true },
            { shapeUrl: "web_editor/Airy/13_001", label: "Airy 13", animated: true },
            { shapeUrl: "web_editor/Airy/14", label: "Airy 14" },
            { shapeUrl: "web_editor/Zigs/01_001", label: "Zigs 01", animated: true },
            { shapeUrl: "web_editor/Zigs/02_001", label: "Zigs 02", animated: true },
            { shapeUrl: "web_editor/Zigs/03", label: "Zigs 03" },
            { shapeUrl: "web_editor/Zigs/04", label: "Zigs 04" },
        ];
    }
    get wavyShapes() {
        return [
            { shapeUrl: "web_editor/Wavy/03", label: "Wavy 01" },
            { shapeUrl: "web_editor/Wavy/10", label: "Wavy 02" },
            { shapeUrl: "web_editor/Wavy/24", label: "Wavy 03", animated: true },
            { shapeUrl: "web_editor/Wavy/26", label: "Wavy 04", animated: true },
            { shapeUrl: "web_editor/Wavy/27", label: "Wavy 05", animated: true },
            { shapeUrl: "web_editor/Wavy/04", label: "Wavy 06" },
            { shapeUrl: "web_editor/Wavy/06_001", label: "Wavy 07" },
            { shapeUrl: "web_editor/Wavy/07", label: "Wavy 08" },
            { shapeUrl: "web_editor/Wavy/08", label: "Wavy 09" },
            { shapeUrl: "web_editor/Wavy/09", label: "Wavy 10" },
            { shapeUrl: "web_editor/Wavy/11", label: "Wavy 11" },
            { shapeUrl: "web_editor/Wavy/28", label: "Wavy 12", animated: true },
            { shapeUrl: "web_editor/Wavy/16", label: "Wavy 13" },
            { shapeUrl: "web_editor/Wavy/17", label: "Wavy 14" },
            { shapeUrl: "web_editor/Wavy/18", label: "Wavy 15" },
            { shapeUrl: "web_editor/Wavy/19", label: "Wavy 16" },
            { shapeUrl: "web_editor/Wavy/22", label: "Wavy 17" },
            { shapeUrl: "web_editor/Wavy/23", label: "Wavy 18" },
        ];
    }
    get blockAndRainyShapes() {
        return [
            { shapeUrl: "web_editor/Blocks/02_001", label: "Blocks 01" },
            { shapeUrl: "web_editor/Rainy/01_001", label: "Rainy 01", animated: true },
            { shapeUrl: "web_editor/Blocks/01_001", label: "Blocks 02" },
            { shapeUrl: "web_editor/Rainy/02_001", label: "Rainy 02", animated: true },
            { shapeUrl: "web_editor/Rainy/06", label: "Rainy 03" },
            { shapeUrl: "web_editor/Blocks/04", label: "Blocks 04" },
            { shapeUrl: "web_editor/Rainy/07", label: "Rainy 04" },
            { shapeUrl: "web_editor/Rainy/10", label: "Rainy 05", animated: true },
            { shapeUrl: "web_editor/Rainy/08_001", label: "Rainy 06", animated: true },
            { shapeUrl: "web_editor/Rainy/09_001", label: "Rainy 07" },
        ];
    }
    get floatingShapes() {
        return [
            { shapeUrl: "web_editor/Floats/01", label: "Float 01", animated: true },
            { shapeUrl: "web_editor/Floats/02", label: "Float 02", animated: true },
            { shapeUrl: "web_editor/Floats/03", label: "Float 03", animated: true },
            { shapeUrl: "web_editor/Floats/04", label: "Float 04", animated: true },
            { shapeUrl: "web_editor/Floats/05", label: "Float 05", animated: true },
            { shapeUrl: "web_editor/Floats/06", label: "Float 06", animated: true },
            { shapeUrl: "web_editor/Floats/07", label: "Float 07", animated: true },
            { shapeUrl: "web_editor/Floats/08", label: "Float 08", animated: true },
            { shapeUrl: "web_editor/Floats/09", label: "Float 09", animated: true },
            { shapeUrl: "web_editor/Floats/10", label: "Float 10", animated: true },
            { shapeUrl: "web_editor/Floats/11", label: "Float 11", animated: true },
            { shapeUrl: "web_editor/Floats/12", label: "Float 12", animated: true },
            { shapeUrl: "web_editor/Floats/13", label: "Float 13", animated: true },
            { shapeUrl: "web_editor/Floats/14", label: "Float 14", animated: true },
        ];
    }
    get allPossiblesShapes() {
        return [
            { shapeUrl: "", label: "" },
            ...this.connectionShapes,
            ...this.originShapes,
            ...this.boldShapes,
            ...this.blobShapes,
            ...this.airyAndZigShapes,
            ...this.wavyShapes,
            ...this.blockAndRainyShapes,
            ...this.floatingShapes,
        ];
    }
    normalize(root) {
        for (const coloredLevelBackgroundParam of this.coloredLevelBackgroundParams) {
            applyFunDependOnSelectorAndExclude(
                this.markColorLevel,
                root,
                coloredLevelBackgroundParam.selector,
                coloredLevelBackgroundParam.exclude
            );
        }
    }
    markColorLevel(editingEl) {
        editingEl.classList.add("o_colored_level");
    }
}
registry.category("website-plugins").add(BackgroundOptionPlugin.id, BackgroundOptionPlugin);

export class BackgroundComponent extends Component {
    static template = "html_builder.BackgroundComponent";
    static components = {
        ...defaultBuilderComponents,
        BackgroundImage,
        BackgroundPosition,
        BackgroundShape,
    };
    static props = {
        withColors: { type: Boolean },
        withImages: { type: Boolean },
        withColorCombinations: { type: Boolean },
        withGradient: { type: Boolean },
        withShapes: { type: Boolean, optional: true },
        getShapeData: { type: Function },
        getShapeStyleUrl: { type: Function },
        shapesInfo: { type: Object },
    };
    static defaultProps = {
        withShapes: false,
    };
    setup() {
        this.isActiveItem = useIsActiveItem();
    }
    showBackgroundShapes() {
        this.env.openCustomizeComponent(BackgroundShapeComponent, this.env.getEditingElements(), {
            getShapeStyleUrl: this.props.getShapeStyleUrl.bind(this),
            shapesInfo: this.props.shapesInfo,
        });
    }
}
