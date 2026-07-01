import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { onMounted, proxy } from "@odoo/owl";
import { useDomState } from "@html_builder/core/utils";
import { useService } from "@web/core/utils/hooks";
import { useCachedModel } from "@html_builder/core/cached_model_utils";
import { registry } from "@web/core/registry";
import wUtils from "@website/js/utils";

export class ProductTemplateOption extends BaseOptionComponent {
    static id = "product_template_option";
    static template = "website_sale.ProductTemplateOption";

    setup() {
        super.setup();

        this.fields = useService("field");
        this.cachedModel = useCachedModel();
        this.modelEdit = undefined;
        this.state = proxy({
            searchModel: "product.template",
        });
        this.domState = useDomState(async (el) => {
            const productTemplate = el.querySelector('[data-oe-model="product.template"]');

            const model = "product.template";
            const field = "product_tag_ids";
            const productId = productTemplate ? parseInt(productTemplate.dataset.oeId) : null;
            const selection = this.modelEdit && this.modelEdit.has(field) ? this.modelEdit.get(field) : [];

            return {
                model,
                field,
                productId,
                selection,
            };
        });

        onMounted(async () => {
            await this.setupFields();
        });
    }

    async setupFields() {
        const [record] = await this.cachedModel.ormRead(
            this.domState.model,
            [this.domState.productId],
            [this.domState.field]
        );

        const selectedRecordIds = record[this.domState.field];
        const modelData = await this.fields.loadFields(this.domState.model, {
            fieldNames: [this.domState.field],
        });
        this.state.searchModel = modelData[this.domState.field].relation;
        this.modelEdit = this.cachedModel.useModelEdit({
            model: this.domState.model,
            recordId: this.domState.productId,
        });
        if (!this.modelEdit.has(this.domState.field)) {
            const storedSelection = await this.cachedModel.ormRead(
                this.state.searchModel,
                selectedRecordIds,
                ["display_name"]
            );
            for (const item of storedSelection) {
                item.name = item.display_name;
            }
            this.modelEdit.init(this.domState.field, [...storedSelection]);
        }
        this.domState.selection = this.modelEdit.get(this.domState.field);
    }

    setSelection(newSelection) {
        const previousSelection = this.domState.selection;
        this.modelEdit.set(this.domState.field, newSelection);
        this.env.editor.shared.history.commit();
        this.applyTags(previousSelection, newSelection);
    }

    async create(name) {
        const [tagId] = await this.env.services.orm.create(this.state.searchModel, [{
            name: name,
        }]);

        this.setSelection([
            ...this.domState.selection,
            {
                id: tagId,
                name: name,
                display_name: name,
                model: this.state.searchModel,
            },
        ]);
    }

    applyTags(oldTags, newTags) {
        const tagListEl = this.env.getEditingElement().querySelector(".o_product_tags");
        const addedTags = newTags.filter(
            (tag) => !oldTags.some((current) => current.id === tag.id)
        );
        const removedTags = oldTags.filter(
            (current) => !newTags.some((tag) => tag.id === current.id)
        );

        for (const tag of removedTags) {
            const tagEl = tagListEl.querySelector(
                `a:has([data-oe-model="product.tag"][data-oe-id="${tag.id}"]), a:has([data-oe-model="product.tag"][data-oe-id="${tag.id}"])`
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

registry.category("website-options").add(ProductTemplateOption.id, ProductTemplateOption);
