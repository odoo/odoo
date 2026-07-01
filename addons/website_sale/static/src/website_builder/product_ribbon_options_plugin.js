import { proxy } from "@odoo/owl";
import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class ProductsRibbonOptionPlugin extends Plugin {
    static id = 'productsRibbonOptionPlugin';
    static shared = [
        'getRibbonsObject',
        'setRibbonObject',
        'addRibbon',
        'getRibbons',
        'setRibbon',
        'deleteRibbon',
        '_setRibbon',
        'setProductTemplateID',
        'getProductTemplateID',
        'addProductTemplatesRibbons',
        'addProductVariantsRibbons',
        '_addRibbon',
        'loadInfo',
        'getCount',
    ];
    count = proxy({ value: 0 });

    resources = {
        builder_actions: {
            SetRibbonAction,
            CreateRibbonAction,
            ModifyRibbonAction,
            DeleteRibbonAction,
        },
    };

    setup() {
        this.positionClasses = { left: "o_left", right: "o_right" };
        this.styleClasses = { ribbon: "o_wsale_ribbon", tag: "o_wsale_badge" };
        this.productTemplatesRibbons = [];
        this.productVariantsRibbons = [];
        this.editMode = false;
    }
    getCount() {
        return this.count;
    }
    /**
     * Get the server ID for a ribbon.
     *
     * Resolves the ID from `originalRibbons` or `ribbonsObject`. Falls back to
     * the provided `ribbonId` if no mapped server ID is found.
     *
     * @param {number} ribbonId
     * @returns {number}
     */
    getServerId(ribbonId) {
        return (
            this.originalRibbons?.[ribbonId]?.serverId ??
            this.ribbonsObject?.[ribbonId]?.serverId ??
            ribbonId
        );
    }

    async loadInfo() {
        if (!this.ribbons) {
            const result = await this.services.orm.searchRead(
                'product.ribbon',
                [['assign', '=', 'manual']],
                ['id', 'name', 'bg_color', 'text_color', 'position', 'style']
            );
            this.ribbons = proxy(result);
        }

        this.ribbonsObject = this.ribbons.reduce((acc, ribbon) => {
            acc[ribbon.id] = ribbon;
            return acc;
        }, {});

        this.originalRibbons = JSON.parse(JSON.stringify(this.ribbonsObject));

        return this.ribbons;
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

    _saveModelRibbons(entries, idKey, model, field, promises) {
        const final = {};
        for (const entry of entries) {
            final[entry[idKey]] = entry.ribbonId;
        }
        const byRibbon = {};
        for (const [recordId, ribbonId] of Object.entries(final)) {
            (byRibbon[this.getServerId(ribbonId)] ||= []).push(parseInt(recordId));
        }
        for (const [ribbonIdStr, ids] of Object.entries(byRibbon)) {
            promises.push(
                this.services.orm.write(model, ids, { [field]: parseInt(ribbonIdStr) || false })
            );
        }
    }

    async _saveRibbons() {
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
        if (created.length > 0) {
            createdRibbonProms.push(
                this.services.orm.create(
                    'product.ribbon',
                    created.map(({ id, serverId, ...ribbon }) => ribbon)
                ).then((ids) => {
                    // Map each created ribbon's local ID to its server ID
                    created.forEach((ribbon, index) => {
                        ribbon.serverId = ids[index];
                        this.originalRibbons[ribbon.id] = Object.assign({}, ribbon);
                    });
                })
            );
        }
        await Promise.all(createdRibbonProms);

        const proms = [];
        for (const ribbon of modified) {
            const ribbonData = {
                name: ribbon.name,
                bg_color: ribbon.bg_color,
                text_color: ribbon.text_color,
                position: ribbon.position,
                style: ribbon.style,
            };
            const serverId = this.getServerId(ribbon.id);
            proms.push(this.services.orm.write('product.ribbon', [serverId], ribbonData));
            this.originalRibbons[ribbon.id] = { ...ribbon, serverId };
        }

        if (deletedIds.length > 0) {
            const serverIds = deletedIds.map((id) => this.getServerId(id));
            proms.push(this.services.orm.unlink("product.ribbon", serverIds));
        }

        await Promise.all(proms);

        const promises = [];
        this._saveModelRibbons(
            this.productTemplatesRibbons, 'templateId', 'product.template', 'website_ribbon_id', promises,
        );
        this._saveModelRibbons(
            this.productVariantsRibbons, 'variantId', 'product.product', 'variant_ribbon_id', promises,
        );
        return Promise.all(promises);
    }

    /**
     * Deletes a ribbon.
     *
     */
    async deleteRibbon(editingElement) {
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
        this.productTemplateID = parseInt(
            editingElement
                .querySelector('[data-oe-model="product.template"]')
                .getAttribute("data-oe-id")
        );
        const ribbons = editingElement.ownerDocument.querySelectorAll(
            `[data-ribbon-id="${ribbonId}"]`
        );
        ribbons.forEach((ribbonElement) => {
            ribbonElement.classList.add("d-none");
            ribbonElement.dataset.ribbonId = "";
            if (isProductPage) {
                this.addProductTemplatesRibbons({
                    templateId: this.productTemplateID,
                    ribbonId: false,
                });
            } else {
                const oeProduct = ribbonElement.closest('.oe_product');
                const variantId = oeProduct?.dataset.variantId
                    ? parseInt(oeProduct.dataset.variantId)
                    : null;
                if (variantId) {
                    this.addProductVariantsRibbons({
                        variantId: variantId,
                        ribbonId: false,
                    });
                } else {
                    const productArticle = ribbonElement.closest('article.oe_product_cart');
                    const templateElement = productArticle?.querySelector('[data-oe-model="product.template"]');
                    const templateId = templateElement ? parseInt(templateElement.getAttribute('data-oe-id')) : null;
                    if (templateId && !isNaN(templateId)) {
                        this.addProductTemplatesRibbons({
                            templateId: templateId,
                            ribbonId: false,
                        });
                    }
                }
            }
        });
        await this._saveRibbons();
    }
    getProductTemplateID() {
        return this.productTemplateID;
    }
    setProductTemplateID(id) {
        this.productTemplateID = id
    }
    /**
     * Add or update a product template's ribbon assignment.
     * Ensures each template has only one ribbon entry.
     *
     * @param {Object} params
     * @param {number} params.templateId - Product template ID
     * @param {number|string|false} params.ribbonId - Ribbon ID to assign
     */
    addProductTemplatesRibbons({ templateId, ribbonId }) {
        // Ensure one entry per template
        const index = this.productTemplatesRibbons.findIndex(
            (entry) => entry.templateId === templateId
        );
        if (index !== -1) {
            this.productTemplatesRibbons[index].ribbonId = ribbonId;
        } else {
            this.productTemplatesRibbons.push({ templateId, ribbonId });
        }
    }
    addProductVariantsRibbons({ variantId, ribbonId }) {
        const index = this.productVariantsRibbons.findIndex(
            (entry) => entry.variantId === variantId
        );
        if (index !== -1) {
            this.productVariantsRibbons[index].ribbonId = ribbonId;
        } else {
            this.productVariantsRibbons.push({ variantId, ribbonId });
        }
    }
    _addRibbon(editingElement, ribbonId) {
        const variantId = parseInt(editingElement.dataset.variantId);
        if (variantId) {
            this.addProductVariantsRibbons({ variantId, ribbonId });
            return;
        }
        const templateId = parseInt(
            editingElement
                .querySelector('[data-oe-model="product.template"]')
                .getAttribute('data-oe-id')
        );
        this.setProductTemplateID(templateId);
        this.addProductTemplatesRibbons({ templateId, ribbonId });
    }
    getRibbonsObject() {
        return this.ribbonsObject;
    }
    setRibbonObject(key, value) {
        this.ribbonsObject[key] = value;
    }
    addRibbon(value) {
        this.ribbons.push(value);
    }
    getRibbons() {
        return this.ribbons;
    }
    setRibbon(key, value){
        const index = this.ribbons.findIndex((ribbon) => ribbon.id == key);
        if (index !== -1) {
            this.ribbons[index] = value;
        }
    }
}

export class SetRibbonAction extends BuilderAction {
    static id = 'setRibbon';
    static dependencies = ['productsRibbonOptionPlugin'];
    setup(){
        this.ribbonOptions = this.dependencies.productsRibbonOptionPlugin
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
        this.ribbonOptions._addRibbon(editingElement, value);

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
export class CreateRibbonAction extends BuilderAction {
    static id = 'createRibbon';
    static dependencies = ['productsRibbonOptionPlugin']
    setup(){
        this.ribbonOptions = this.dependencies.productsRibbonOptionPlugin
    }
    apply({ editingElement }) {
        const ribbonId = Date.now();
        this.ribbonOptions._addRibbon(editingElement, ribbonId);
        const ribbon = proxy({
            serverId: null,
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
export class ModifyRibbonAction extends BuilderAction {
    static id = 'modifyRibbon';
    static dependencies = ['productsRibbonOptionPlugin', 'history'];
    setup() {
        this.ribbonOptions = this.dependencies.productsRibbonOptionPlugin
    }
    getValue({ editingElement, params }) {
        const ribbonId = parseInt(
            editingElement.querySelector('.o_ribbons')?.dataset.ribbonId
        );
        if (!ribbonId || !this.ribbonOptions.getRibbonsObject().hasOwnProperty(ribbonId)) {
            return;
        }

        return this.ribbonOptions.getRibbonsObject()[ribbonId][params.mainParam];
    }
    isApplied({ editingElement, params, value }) {
        let ribbonId = parseInt(
            editingElement.querySelector('.o_ribbons')?.dataset.ribbonId
        );
        if (!ribbonId || !this.ribbonOptions.getRibbonsObject().hasOwnProperty(ribbonId)) {
            return;
        }
        return this.ribbonOptions.getRibbonsObject()[ribbonId][params.mainParam] === value;
    }
    async apply({ editingElement, params, value }) {
        const isPreviewMode = this.dependencies.history.getIsPreviewing();
        const ribbonEl = editingElement.querySelector('.o_ribbons')
        const setting = params.mainParam;
        const ribbonId = parseInt(ribbonEl.dataset.ribbonId);
        const previousRibbon = this.ribbonOptions.getRibbonsObject()[ribbonId];
        this.ribbonOptions.setRibbonObject(ribbonId, {...previousRibbon, [setting]: value});
        this.ribbonOptions.setRibbon(ribbonId, {...previousRibbon, [setting]: value});
        const res = await this.ribbonOptions._setRibbon(
            ribbonEl,
            { ...previousRibbon, [setting]: value },
            !isPreviewMode
        );
        if(isPreviewMode){
            this.ribbonOptions.setRibbonObject(ribbonId, previousRibbon)
            this.ribbonOptions.setRibbon(ribbonId, previousRibbon)
        }
        return res
    }
}
export class DeleteRibbonAction extends BuilderAction {
    static id = 'deleteRibbon';
    static dependencies = ['productsRibbonOptionPlugin'];
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
        return this.dependencies.productsRibbonOptionPlugin.deleteRibbon(editingElement);
    }
}

registry.category('website-plugins').add(
    ProductsRibbonOptionPlugin.id, ProductsRibbonOptionPlugin,
);
