import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

export class AddressFormOptionPlugin extends Plugin {
    static id = "addressFormOption";
    resources = {
        builder_actions: { SetAddressFormValueAction },
    };
}

export class SetAddressFormValueAction extends BuilderAction {
    static id = "setAddressFormValue";

    setup() {
        this.preview = false;
    }

    getValue({ editingElement: el, params: { property, text, fallback } }) {
        const value = el.style.getPropertyValue(property);
        if (!value) {
            return fallback ? getComputedStyle(el).getPropertyValue(fallback) : undefined;
        }
        return text ? JSON.parse(value) : value;
    }

    async apply({ editingElement: el, params: { property, field, text }, value }) {
        el.style.setProperty(property, text ? JSON.stringify(value) : value);
        await rpc("/shop/config/website", { [field]: value });
    }
}

registry.category("website-plugins").add(AddressFormOptionPlugin.id, AddressFormOptionPlugin);
