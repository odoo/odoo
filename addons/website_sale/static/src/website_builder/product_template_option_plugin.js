import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import wUtils from "@website/js/utils";

export class ProductTemplateOptionPlugin extends Plugin {
    static id = "productTemplateOptionPlugin";
    resources = {
        builder_actions: {
            CreateTagAction,
            SetTagsAction,
        },
        builder_options_render_context: {
            productTemplateOptionSelector: ".o_wsale_product_page:has(.variant_attribute)",
        },
    };
}

export class CreateTagAction extends BuilderAction {
    static id = "createTagAction";

    async load({ value }) {
        const [id] = await this.services.orm.create("product.tag", [{ name: value }]);
        return id;
    }
}

export class SetTagsAction extends BuilderAction {
    static id = "setTagsAction";

    async apply({ editingElement, value, params }) {
        const newTags = JSON.parse(value)
        const { oldSelection } = params
        this.applyTags(editingElement, oldSelection, newTags);
    }

    applyTags(editingElement, oldTags, newTags) {
        const tagListEl = editingElement.querySelector(".o_product_tags");
        const addedTags = newTags.filter(
            (tag) => !oldTags.some((current) => current.id === tag.id)
        );
        const removedTags = oldTags.filter(
            (current) => !newTags.some((tag) => tag.id === current.id)
        );

        for (const tag of removedTags) {
            const tagEl = tagListEl.querySelector(
                `a:has([data-oe-model="product.tag"][data-oe-id="${tag.id}"])`
            );
            tagEl?.remove();
        }

        for (const tag of addedTags) {
            if (!tagListEl.children?.length) {
                tagListEl.className =
                    "o_product_tags o_field_tags d-flex flex-wrap align-items-center gap-2 mb-2 mt-1";
            }

            const newTagLink = document.createElement("a");
            newTagLink.className = "text-decoration-none d-inline-block";
            newTagLink.href = `/shop?tags=${wUtils.slugify(tag.name)}-${tag.id}`;

            const newTagEl = document.createElement("span");
            newTagEl.className = "order-1 p-2 rounded lh-1 small text-nowrap o_savable";
            newTagEl.style = "background-color: #3C3C3C33; color: #3C3C3C;";
            newTagEl.dataset.oeModel = "product.tag";
            newTagEl.dataset.oeId = tag.id;
            newTagEl.dataset.oeType = "char";
            newTagEl.dataset.oeField = "name";
            newTagEl.dataset.oeExpression = "tag.name";
            newTagEl.textContent = tag.name;
            newTagEl.contentEditable = "true";

            newTagLink.appendChild(newTagEl);
            tagListEl.appendChild(newTagLink);
        }
    }
}

registry
    .category("website-plugins")
    .add(ProductTemplateOptionPlugin.id, ProductTemplateOptionPlugin);
