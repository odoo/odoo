import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
class CustomersAvatarsOptionPlugin extends Plugin {
    static id = "customersAvatarOption";
    selector = ".s_customers_avatars";
    resources = {
        builder_options: [
            {
                template: "website.CustomersAvatarsOption",
                selector: this.selector,
            },
        ],
        builder_actions: {
            customersAvatarsRoundness: {
                getValue: ({ editingElement }) => {
                    for (let x = 0; x <= 5; x++) {
                        if (editingElement.classList.contains(`rounded-${x}`)) {
                            return x;
                        }
                    }
                    return 0;
                },
                apply: ({ editingElement, value }) => {
                    for (let x = 0; x <= 5; x++) {
                        editingElement.classList.remove(`rounded-${x}`);
                    }
                    editingElement.classList.add(`rounded-${value}`);
                },
            },
        },
        so_content_addition_selector: [".s_customers_avatars"],
    };
}
registry.category("website-plugins").add(CustomersAvatarsOptionPlugin.id, CustomersAvatarsOptionPlugin);
