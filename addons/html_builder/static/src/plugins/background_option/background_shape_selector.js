import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { ShapeSelector } from "@html_builder/plugins/shape/shape_selector";

export class BackgroundShapeSelector extends BaseOptionComponent {
    static template = "html_builder.BackgroundShapeSelector";
    static dependencies = ["backgroundShapeOption"];
    static components = { ShapeSelector };
    static props = {
        ...ShapeSelector.props,
    };
    setup() {
        super.setup();
        this.backgroundShapePlugin = this.dependencies.backgroundShapeOption;
        this.state = useDomState((editingElement) => ({
            shapeStyle: this.getShapeStyleDomUpdated(editingElement),
        }));
    }
    get shapeSelectorProps() {
        return { ...this.props, getShapeStyle: this.getShapeStyle.bind(this) };
    }
    getShapeStyle(shapePath) {
        return this.state.shapeStyle[shapePath];
    }
    getShapeStyleDomUpdated(editingEl) {
        const shapeStyleMap = {};
        for (const group of Object.values(this.props.shapeGroups)) {
            for (const subgroup of Object.values(group.subgroups)) {
                for (const [shapePath] of Object.entries(subgroup.shapes)) {
                    const shapeData = this.backgroundShapePlugin.getShapeData(editingEl);
                    shapeData.shape = shapePath;
                    shapeData.colors = this.backgroundShapePlugin.getImplicitColors(
                        editingEl,
                        shapePath,
                        shapeData.colors
                    );
                    let backgroundPosition = "";
                    if (shapeData.flip) {
                        const [xPos, yPos] = this.backgroundShapePlugin.getShapeStylePosition(
                            shapeData.shape,
                            shapeData.flip
                        );

                        backgroundPosition = `background-position: ${xPos}% ${yPos}%`;
                    }
                    const shapeStyle = `background-image: url(${this.backgroundShapePlugin.getShapeSrc(
                        shapeData
                    )}); ${backgroundPosition}`;
                    shapeStyleMap[shapePath] = shapeStyle;
                }
            }
        }
        return shapeStyleMap;
    }
}
