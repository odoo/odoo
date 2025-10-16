import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class MediaSizeOptionPlugin extends Plugin {
    static id = "MediaSizeOptionPlugin";
    resources = {
        builder_actions: {
            MediaSizeSliderAction,
            MediaSizeTextAction,
            SetMediaSizeAutoAction,
        },
    };
}

function setWidth(getAction, editingElement, value) {
    getAction("styleAction").apply({
        editingElement,
        params: {
            mainParam: "width",
        },
        value: value,
    });
}

export class MediaSizeSliderAction extends BuilderAction {
    static id = "mediaSizeSlider";
    static dependencies = ["builderActions"];
    getValue({ editingElement }) {
        return parseInt(editingElement.style.width) || 100;
    }
    apply({ editingElement, value }) {
        setWidth(this.dependencies.builderActions.getAction, editingElement, value + "%");
    }
}

export class MediaSizeTextAction extends BuilderAction {
    static id = "mediaSizeText";
    static dependencies = ["builderActions"];
    getValue({ editingElement }) {
        // If width is set to "auto", we return an empty string to display the
        // text input placeholder.
        const width = editingElement.style.width;
        return width === "auto" ? "" : width;
    }
    apply({ editingElement, value }) {
        if (value === "") {
            setWidth(this.dependencies.builderActions.getAction, editingElement, "auto");
            return;
        }
        if (value.endsWith("%")) {
            value = value.slice(0, -1);
        }
        if (isNaN(value) || value == 0) {
            setWidth(this.dependencies.builderActions.getAction, editingElement, "auto");
            return;
        }
        value = Math.min(Math.max(value, 10), 100);
        setWidth(this.dependencies.builderActions.getAction, editingElement, value + "%");
    }
}

export class SetMediaSizeAutoAction extends BuilderAction {
    static id = "setMediaSizeAuto";
    static dependencies = ["builderActions"];
    isApplied({ editingElement }) {
        // The "Auto" button is active when width is auto or not set
        return editingElement.style.width === "auto" || editingElement.style.width === "";
    }
    apply({ editingElement }) {
        setWidth(this.dependencies.builderActions.getAction, editingElement, "auto");
    }
}

registry.category("builder-plugins").add(MediaSizeOptionPlugin.id, MediaSizeOptionPlugin);
