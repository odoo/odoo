import { BuilderAction } from "@html_builder/core/builder_action";
import { SNIPPET_SPECIFIC_NEXT } from "@html_builder/utils/option_sequence";
import { withSequence } from "@html_editor/utils/resource";
import { reactive } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { ProductVariantRibbonOption } from "./product_variant_ribbon_option";
import {
    ProductsRibbonOptionPlugin,
    SetRibbonAction,
    CreateRibbonAction,
    ModifyRibbonAction
} from "./product_ribbon_options_plugin";

class ProductVariantRibbonOptionPlugin extends ProductsRibbonOptionPlugin {
    static id = 'productVariantRibbonOptionPlugin';
    static shared = [
        'getRibbonsObject',
        'setRibbonObject',
        'addRibbon',
        'getRibbons',
        'setRibbon',
        'deleteRibbon',
        '_setRibbon',
        'setProductVariantID',
        'getProductVariantID',
        'addProductVariantsRibbons',
        'setProductTemplateID',
        'getProductTemplateID',
        'addProductTemplatesRibbons',
        'loadInfo',
        'getCount',
    ];
    resources = {
        builder_options: [
            withSequence(SNIPPET_SPECIFIC_NEXT, ProductVariantRibbonOption),
        ],
        builder_actions: {
            SetTemplateRibbonAction,
            SetVariantRibbonAction,
            CreateTemplateRibbonAction,
            CreateVariantRibbonAction,
            ModifyVariantRibbonAction,
            DeleteVariantRibbonAction,
        },
    };

    setup() {
        super.setup();
        this.productVariantsRibbons = [];
    }

    async _setRibbon(editingElement, ribbon, save = true) {
        const ribbonId = ribbon.id;
        const editableBody = editingElement.ownerDocument.body;
        editingElement.dataset.ribbonId = ribbonId;

        // Update all ribbons with this ID
        const ribbons = editableBody.ownerDocument.querySelectorAll(
            `[data-ribbon-id="${ribbonId}"]`,
        );

        for (const ribbonElement of ribbons) {
            ribbonElement.textContent = ribbon.name;
            ribbonElement.classList.remove('o_wsale_ribbon', 'o_wsale_badge', 'o_right', 'o_left');
            if (ribbonElement.classList.contains('d-none')) {
                ribbonElement.classList.remove('d-none');
            }

            ribbonElement.classList.add(
                this.positionClasses[ribbon.position],
                this.styleClasses[ribbon.style],
            );
            ribbonElement.style.backgroundColor = ribbon.bg_color || "";
            ribbonElement.style.color = ribbon.text_color || "";
        }

        return save ? await this._saveRibbons() : "";
    }

    async _saveRibbons() {
        super._saveRibbons();

        const originalIds = Object.keys(this.originalRibbons).map((id) => parseInt(id));
        const currentIds = this.ribbons.map((ribbon) => parseInt(ribbon.id));
        const created = this.ribbons.filter((ribbon) => !originalIds.includes(ribbon.id));
        const deletedIds = originalIds.filter((id) => !currentIds.includes(id));
        const modified = this.ribbons.filter((ribbon) => {
            if (created.includes(ribbon)) {
                return false;
            }
            const original = this.originalRibbons[ribbon.id];
            return Object.entries(ribbon).some(([key, value]) => value !== original[key]);
        });

        const createdRibbonProms = [];
        let createdRibbonIds;
        if (created.length > 0) {
            createdRibbonProms.push(
                this.services.orm.create(
                    'product.ribbon',
                    created.map((ribbon) => {
                        ribbon = Object.assign({}, ribbon);
                        this.originalRibbons[ribbon.id] = ribbon;
                        delete ribbon.id;
                        return ribbon;
                    })
                ).then((ids) => (createdRibbonIds = ids))
            );
        }
        await Promise.all(createdRibbonProms);

        const localToServer = Object.assign(
            this.ribbonsObject,
            Object.fromEntries(
                created.map((ribbon, index) => [
                    ribbon.id,
                    { ...this.ribbonsObject[ribbon.id], id: createdRibbonIds[index] },
                ])
            ),
            {
                false: {
                    id: "",
                },
            }
        );

        const proms = [];
        for (const ribbon of modified) {
            const ribbonData = {
                name: ribbon.name,
                bg_color: ribbon.bg_color,
                text_color: ribbon.text_color,
                position: ribbon.position,
                style: ribbon.style,
            };
            const serverId = localToServer[ribbon.id]?.id || ribbon.id;
            proms.push(this.services.orm.write('product.ribbon', [serverId], ribbonData));
            this.originalRibbons[ribbon.id] = Object.assign({}, ribbon);
        }

        if (deletedIds.length > 0) {
            proms.push(this.services.orm.unlink('product.ribbon', deletedIds));
        }

        await Promise.all(proms);

        // Building the final variant to ribbon-id map so that we can remove duplicate entries
        const finalVariantRibbons = this.productVariantsRibbons.reduce(
            (acc, { variantId, ribbonId }) => {
                acc[variantId] = ribbonId;
                return acc;
            }, {},
        );
        // Inverting the relationship so that we have all variants that have the same ribbon to
        // reduce RPCs
        const ribbonVariants = {};
        for (const [variantId, ribbonId] of Object.entries(finalVariantRibbons)) {
            const rid = ribbonVariants[ribbonId] ||= [];
            rid.push(parseInt(variantId));
        }

        const promises = [];
        for (const ribbonId in ribbonVariants) {
            const variantIds = ribbonVariants[ribbonId];
            const parsedId = parseInt(ribbonId);
            const validRibbonId = currentIds.includes(parsedId) ? ribbonId : false;
            promises.push(
                this.services.orm.write('product.product', variantIds, {
                    variant_ribbon_id: localToServer[validRibbonId]?.id || false,
                })
            );
        }

        return Promise.all(promises);
    }

    /**
     * Deletes a ribbon.
     *
     */
    deleteRibbon(editingElement) {
        super.deleteRibbon(editingElement);

        const ribbonId = parseInt(editingElement.querySelector('.o_ribbons')?.dataset.ribbonId);
        if (this.ribbonsObject[ribbonId]) {
            const ribbonIndex = this.ribbons.findIndex(ribbon => ribbon.id === ribbonId);
            if (ribbonIndex !== -1 ) {
                this.ribbons.splice(ribbonIndex, 1);
            }
            delete this.ribbonsObject[ribbonId];

            // update "reactive" count to trigger rerendering the BuilderSelect component (which
            // has the value as a t-key)
            this.count.value++;
        }
        const isProductPage = editingElement.ownerDocument.querySelector('#product_detail');
        this.productVariantID = parseInt(
            editingElement
                .querySelector('[data-oe-model="product.product"]')
                .getAttribute("data-oe-id")
        );
        const ribbons = editingElement.ownerDocument.querySelectorAll(
            `[data-ribbon-id="${ribbonId}"]`
        );
        ribbons.forEach((ribbonElement) => {
            ribbonElement.classList.add("d-none");
            ribbonElement.dataset.ribbonId = "";
            let variantId;
            if (isProductPage) {
                variantId = this.productVariantID;
            } else {
                // Find the product variant ID from the ribbon element's parent article.
                const productArticle = ribbonElement.closest('article.oe_product_cart');
                const variantElement = productArticle?.querySelector('[data-oe-model="product.product"]');
                variantId = variantElement ? parseInt(variantElement.getAttribute('data-oe-id')) : null;
            }
            if (variantId && !isNaN(variantId)) {
                this.productVariantsRibbons.push({
                    variantId: variantId,
                    ribbonId: false,
                });
            }
        });
        this._saveRibbons();
    }
    getProductVariantID() {
        return this.productVariantID;
    }
    setProductVariantID(id) {
        this.productVariantID = id
    }
    addProductVariantsRibbons(value) {
        this.productVariantsRibbons.push(value);
    }
}

class SetTemplateRibbonAction extends SetRibbonAction {
    static id = 'setTemplateRibbon';
    static dependencies = ['productVariantRibbonOptionPlugin'];
    setup(){
        this.ribbonOptions = this.dependencies.productVariantRibbonOptionPlugin
    }
}
class SetVariantRibbonAction extends BuilderAction {
    static id = 'setVariantRibbon';
    static dependencies = ['productVariantRibbonOptionPlugin'];
    setup(){
        this.ribbonOptions = this.dependencies.productVariantRibbonOptionPlugin
    }
    isApplied({ editingElement, value }) {
        const ribbonId = parseInt(
            editingElement.querySelector('.o_ribbons')?.dataset.ribbonId,
        );
        const match = !ribbonId || !this.ribbonOptions.getRibbonsObject().hasOwnProperty(ribbonId)
            ? ''
            : ribbonId;
        return match === value;
    }
    apply({ isPreviewing, editingElement, value }) {
        const productVariantID = parseInt(
            editingElement
                .querySelector('[data-oe-model="product.product"]')
                .getAttribute('data-oe-id')
        );
        this.ribbonOptions.setProductVariantID(productVariantID)
        this.ribbonOptions.addProductVariantsRibbons({
            variantId: productVariantID,
            ribbonId: value,
        });

        const ribbon = this.ribbonOptions.getRibbonsObject()[value] || {
            id: '',
            name: '',
            bg_color: '',
            text_color: '',
            position: 'left',
            style: 'ribbon',
        };

        return this.ribbonOptions._setRibbon(
            editingElement.querySelector('.o_ribbons'),
            ribbon,
            !isPreviewing,
        );
    }
}
class CreateTemplateRibbonAction extends CreateRibbonAction {
    static id = 'createTemplateRibbon';
    static dependencies = ['productVariantRibbonOptionPlugin'];
    setup(){
        this.ribbonOptions = this.dependencies.productVariantRibbonOptionPlugin
    }
}
class CreateVariantRibbonAction extends BuilderAction {
    static id = 'createVariantRibbon';
    static dependencies = ['productVariantRibbonOptionPlugin']
    setup(){
        this.ribbonOptions = this.dependencies.productVariantRibbonOptionPlugin
    }
    apply({ editingElement }) {
        const productVariantId = editingElement
            .querySelector('[data-oe-model="product.product"]')
            .getAttribute('data-oe-id')
        this.ribbonOptions.setProductVariantID(parseInt(
            productVariantId
        ));
        const ribbonId = Date.now();
        this.ribbonOptions.addProductVariantsRibbons({
            variantId: productVariantId,
            ribbonId: ribbonId,
        });
        const ribbon = reactive({
            id: ribbonId,
            name: 'Ribbon Name',
            bg_color: '',
            text_color: 'purple',
            position: 'left',
            style: 'ribbon',
        });
        this.ribbonOptions.addRibbon(ribbon);
        this.ribbonOptions.setRibbonObject(ribbonId, ribbon);
        return this.ribbonOptions._setRibbon(editingElement.querySelector('.o_ribbons'), ribbon);
    }
}

class ModifyVariantRibbonAction extends ModifyRibbonAction {
    static id = 'modifyVariantRibbon';
    static dependencies = ['productVariantRibbonOptionPlugin', 'history'];
    setup() {
        this.ribbonOptions = this.dependencies.productVariantRibbonOptionPlugin
    }
}

class DeleteVariantRibbonAction extends BuilderAction {
    static id = 'deleteVariantRibbon';
    static dependencies = ['productVariantRibbonOptionPlugin'];
    setup() {
        this.canTimeout = false;
    }
    async apply({ editingElement }) {
        const save = await new Promise((resolve) => {
            this.services.dialog.add(ConfirmationDialog, {
                title: _t("Delete Ribbon"),
                body: _t("It will be removed from all products. Are you sure?"),
                confirmLabel: _t("Delete Ribbon"),
                confirm: () => resolve(true),
                cancel: () => resolve(false),
            });
        });
        if (!save) {
            return;
        }
        return this.dependencies.productVariantRibbonOptionPlugin.deleteRibbon(editingElement);
    }
}

registry.category('website-plugins').add(
    ProductVariantRibbonOptionPlugin.id, ProductVariantRibbonOptionPlugin,
);
