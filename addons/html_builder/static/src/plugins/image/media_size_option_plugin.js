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
        // If width is not set or set to "auto", we arbitrarily set the slider
        // to 99%. 99% seems preferable to 100% because it allows the user to
        // set 100% by acting on the slider. If "auto" was set as 100% instead
        // of 99%, if the user dragged the slider towards the right, the preview
        // mechanism would prevent 100% from being set, and the setting would
        // stay at "auto".
        const width = editingElement.style.width;
        if (width === "auto" || width === "") {
            return "99%";
        }
        return width;
    }
    apply({ editingElement, value }) {
        setWidth(this.dependencies.builderActions.getAction, editingElement, value);
    }
}

export class MediaSizeTextAction extends BuilderAction {
    static id = "mediaSizeText";
    static dependencies = ["builderActions"];
    getValue({ editingElement }) {
        // If width is set to "auto", we return an empty string to display the
        // BuilderNumberInput placeholder text.
        const width = editingElement.style.width;
        return width === "auto" ? "" : width;
    }
    apply({ editingElement, value }) {
        if (!value || value === "") {
            setWidth(this.dependencies.builderActions.getAction, editingElement, "auto");
            return;
        }
        setWidth(this.dependencies.builderActions.getAction, editingElement, value);
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
    clean({ editingElement }) {
        setWidth(this.dependencies.builderActions.getAction, editingElement, "100%");
    }
}

registry.category("builder-plugins").add(MediaSizeOptionPlugin.id, MediaSizeOptionPlugin);
