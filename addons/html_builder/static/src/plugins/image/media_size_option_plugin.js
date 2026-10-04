import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

/**
 * @typedef {((width: string, editingElement: HTMLElement) => width)[]} read_media_size_width_processors
 * @typedef {((width: string, editingElement: HTMLElement) => width)[]} write_media_size_width_processors
 */

class MediaSizeOptionPlugin extends Plugin {
    static id = "mediaSizeOption";
    resources = {
        builder_actions: {
            MediaSizeSliderAction,
            MediaSizeTextAction,
            SetMediaSizeAutoAction,
        },
    };
}

class MediaSizeAction extends BuilderAction {
    static dependencies = ["builderActions"];
    readWidth(editingElement) {
        const width = editingElement.style.width;
        return this.processThrough("read_media_size_width_processors", width, editingElement);
    }
    writeWidth(editingElement, value) {
        value = this.processThrough("write_media_size_width_processors", value, editingElement);
        this.dependencies.builderActions
            .getAction("styleAction")
            .apply({ editingElement, params: { mainParam: "width" }, value });
    }
}

export class MediaSizeSliderAction extends MediaSizeAction {
    static id = "mediaSizeSlider";
    getValue({ editingElement }) {
        // If width is not set or set to "auto", we arbitrarily set the slider
        // to 99%. 99% seems preferable to 100% because it allows the user to
        // set 100% by acting on the slider. If "auto" was set as 100% instead
        // of 99%, if the user dragged the slider towards the right, the preview
        // mechanism would prevent 100% from being set, and the setting would
        // stay at "auto".
        const width = this.readWidth(editingElement);
        if (width === "auto" || width === "") {
            return "99%";
        }
        return width;
    }
    apply({ editingElement, value }) {
        this.writeWidth(editingElement, value);
    }
}

export class MediaSizeTextAction extends MediaSizeAction {
    static id = "mediaSizeText";
    getValue({ editingElement }) {
        // If width is set to "auto", we return an empty string to display the
        // BuilderNumberInput placeholder text.
        const width = this.readWidth(editingElement);
        return width === "auto" ? "" : width;
    }
    apply({ editingElement, value }) {
        if (!value || value === "") {
            this.writeWidth(editingElement, "auto");
            return;
        }
        this.writeWidth(editingElement, value);
    }
}

export class SetMediaSizeAutoAction extends MediaSizeAction {
    static id = "setMediaSizeAuto";
    isApplied({ editingElement }) {
        const width = this.readWidth(editingElement);
        // The "Auto" button is active when width is auto or not set
        return width === "auto" || width === "";
    }
    apply({ editingElement }) {
        this.writeWidth(editingElement, "auto");
    }
    clean({ editingElement }) {
        this.writeWidth(editingElement, "100%");
    }
}

registry.category("builder-plugins").add(MediaSizeOptionPlugin.id, MediaSizeOptionPlugin);
