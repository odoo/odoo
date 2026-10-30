import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

export class AddressFormOptionPlugin extends Plugin {
    static id = "addressFormOption";
    resources = {
        builder_actions: { SetAddressFormMarkerAction, SetAddressFormMarkerColorAction },
        dirty_trackers: {
            selector: "#o_wsale_address_form",
            dirtyClass: "o_dirty_address_form",
            match: "self",
        },
        on_ready_to_save_document_handlers: this.onSave.bind(this),
    };

    async onSave() {
        const formEl = this.editable.querySelector("#o_wsale_address_form.o_dirty_address_form");
        if (!formEl) {
            return;
        }
        const classSuffix = (prefix) =>
            [...formEl.classList].find((cls) => cls.startsWith(prefix))?.slice(prefix.length);
        const marker = formEl.style.getPropertyValue("--form-label-marker");
        await rpc("/shop/config/website", {
            address_form_marked_fields: classSuffix("o_mark_"),
            address_form_label_marker: marker && JSON.parse(marker),
            address_form_label_marker_color: formEl.style.getPropertyValue(
                "--form-label-marker-color"
            ),
            address_form_label_position: classSuffix("o_labels_"),
            address_form_label_width: formEl.style.getPropertyValue("--form-label-width"),
        });
        formEl.classList.remove("o_dirty_address_form");
    }
}

export class SetAddressFormMarkerAction extends BuilderAction {
    static id = "setAddressFormMarker";

    getValue({ editingElement: el }) {
        const marker = el.style.getPropertyValue("--form-label-marker");
        return marker && JSON.parse(marker);
    }

    apply({ editingElement: el, value }) {
        if (value) {
            el.style.setProperty("--form-label-marker", JSON.stringify(value));
        } else {
            el.style.removeProperty("--form-label-marker");
        }
    }
}

export class SetAddressFormMarkerColorAction extends BuilderAction {
    static id = "setAddressFormMarkerColor";
    static dependencies = ["builderActions"];

    setup() {
        this.style = this.dependencies.builderActions.getAction("styleAction");
        this.params = { mainParam: "--form-label-marker-color" };
    }

    getValue(args) {
        const color = this.style.getValue({ ...args, params: this.params });
        if (color) {
            return color;
        }
        // Unset, the marker takes the colour of the label holding it
        const label = args.editingElement.querySelector(".col-form-label");
        return label ? getComputedStyle(label).color : "";
    }

    apply(args) {
        this.style.apply({ ...args, params: this.params });
    }
}

registry.category("website-plugins").add(AddressFormOptionPlugin.id, AddressFormOptionPlugin);
