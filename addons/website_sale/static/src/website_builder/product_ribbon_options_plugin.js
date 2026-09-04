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
        'addProductVariantsRibbons',
        'addProductTemplatesRibbons',
        'loadInfo',
        'getCount',
        'isVariantMode',
        'getProductVariantId',
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
        const ribbonEl = editingElement.querySelector(".o_ribbons");
        const ribbonId = ribbon.id;
        const editableBody = ribbonEl.ownerDocument.body;
        const variantMode = this.isVariantMode(editingElement)
        if (variantMode) {
            ribbonEl.dataset.ribbonId = ribbonId;
        } else {
            ribbonEl.dataset.templateRibbonId = ribbonId;
        }

        // Update all ribbons with this ID
        const ribbons = editableBody.ownerDocument.querySelectorAll(
            `[data-template-ribbon-id="${ribbonId}"], [data-ribbon-id="${ribbonId}"]`
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

        const promises = [
            ...this._getRibbonWriteProms(
                this.productTemplatesRibbons, 'product.template', 'website_ribbon_id'
            ),
            ...this._getRibbonWriteProms(
                this.productVariantsRibbons, 'product.product', 'variant_ribbon_id'
            ),
        ];

        return Promise.all(promises);
    }

    /**
     * Builds the ORM write proms that assign a ribbon to a set of records (product templates or
     * variants), grouping records by server ribbon ID to reduce the number of RPCs.
     *
     * @param {Array<Object>} entries - list of { [idKey]: recordId, ribbonId } objects
     * @param {string} idKey - name of the record ID property on each entry
     * @param {string} model - model to write on ("product.template" or "product.product")
     * @param {string} fieldName - ribbon field name on the model
     * @returns {Array<Promise>}
     */
    _getRibbonWriteProms(entries, model, fieldName) {
        // Building the final record to ribbon-id map so that we can remove duplicate entries
        const finalRibbons = entries.reduce(
            (acc, { recordId, ribbonId }) => {
                acc[recordId] = ribbonId;
                return acc;
            }, {},
        );

        // Inverting the relationship so that we have all records that have the same ribbon to
        // reduce RPCs
        const ribbonRecords = {};
        for (const [recordId, ribbonId] of Object.entries(finalRibbons)) {
            const serverRibbonId = this.getServerId(ribbonId);
            const recordIds = (ribbonRecords[serverRibbonId] ||= []);
            recordIds.push(parseInt(recordId));
        }

        const proms = [];
        for (const [ribbonIdStr, recordIds] of Object.entries(ribbonRecords)) {
            const ribbonId = parseInt(ribbonIdStr) || false;
            proms.push(this.services.orm.write(model, recordIds, { [fieldName]: ribbonId }));
        }
        return proms;
    }

    /**
     * Deletes a ribbon.
     *
     */
    async deleteRibbon(editingElement) {
        const ribbonId = parseInt(
            this.isVariantMode(editingElement)
                ? editingElement.querySelector(".o_ribbons")?.dataset?.ribbonId
                : editingElement.querySelector(".o_ribbons")?.dataset?.templateRibbonId
        );
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
        const productTemplateID = parseInt(
            editingElement
                .querySelector('[data-oe-model="product.template"]')
                .getAttribute("data-oe-id")
        );
        const productVariantID = this.getProductVariantId(editingElement);
        const ribbons = editingElement.ownerDocument.querySelectorAll(
            `[data-ribbon-id="${ribbonId}"], [data-template-ribbon-id="${ribbonId}"]`
        );
        ribbons.forEach((ribbonElement) => {
            ribbonElement.classList.add("d-none");
            ribbonElement.dataset.ribbonId = "";
            ribbonElement.dataset.templateRibbonId = "";
            let templateId;
            let variantId;
            if (isProductPage) {
                templateId = productTemplateID;
                variantId = productVariantID;
            } else {
                // Find the product template ID from the ribbon element's parent article.
                const productArticle = ribbonElement.closest('article.oe_product_cart');
                const templateElement = productArticle?.querySelector('[data-oe-model="product.template"]');
                templateId = templateElement ? parseInt(templateElement.getAttribute('data-oe-id')) : null;
                const variantElement = productArticle?.querySelector(
                    '[data-oe-model="product.product"]'
                );
                variantId = variantElement
                    ? parseInt(variantElement.getAttribute("data-oe-id"))
                    : null;
            }
            if (templateId && !isNaN(templateId)) {
                this.addProductTemplatesRibbons({
                    recordId: templateId,
                    ribbonId: false,
                });
            }
            if (variantId && !isNaN(variantId)) {
                this.addProductVariantsRibbons({
                    recordId: variantId,
                    ribbonId: false,
                });
            }
        });
        await this._saveRibbons();
    }
    /**
     * Add or update a product template's ribbon assignment.
     * Ensures each template has only one ribbon entry.
     *
     * @param {Object} params
     * @param {number} params.recordId - Product template ID
     * @param {number|string|false} params.ribbonId - Ribbon ID to assign
     */
    addProductTemplatesRibbons({ recordId, ribbonId }) {
        // Ensure one entry per template
        const index = this.productTemplatesRibbons.findIndex(
            (entry) => entry.recordId === recordId
        );
        if (index !== -1) {
            this.productTemplatesRibbons[index].ribbonId = ribbonId;
        } else {
            this.productTemplatesRibbons.push({ recordId, ribbonId });
        }
    }
    /**
     * Add or update a product variant's ribbon assignment.
     * Ensures each variant has only one ribbon entry.
     *
     * @param {Object} params
     * @param {number} params.recordId - Product variant ID
     * @param {number|string|false} params.ribbonId - Ribbon ID to assign
     */
    addProductVariantsRibbons({ recordId, ribbonId }) {
        // Ensure one entry per variant
        const index = this.productVariantsRibbons.findIndex(
            (entry) => entry.recordId === recordId
        );
        if (index !== -1) {
            this.productVariantsRibbons[index].ribbonId = ribbonId;
        } else {
            this.productVariantsRibbons.push({ recordId, ribbonId });
        }
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
    setRibbon(key, value) {
        const index = this.ribbons.findIndex((ribbon) => ribbon.id == key);
        if (index !== -1) {
            this.ribbons[index] = value;
        }
    }

    isVariantMode(editingElement) {
        const productTemplate = editingElement.querySelector('[data-oe-model="product.template"]');
        const templateId = productTemplate ? parseInt(productTemplate.dataset.oeId) : null;
        return (
            (editingElement.closest("#product_detail") &&
                editingElement.querySelector(".variant_attribute")) ||
            !templateId
        );
    }

    /**
     * Resolve a variant's id from its "t-field" reference in the DOM ("data-oe-model"), or its
     * "data-wsale-*" equivalent when its main image is a showcase video: that element isn't a
     * real "t-field" reference, so it doesn't carry "data-oe-model" (see "shop_product_image").
     */
    getProductVariantId(editingElement) {
        const el = editingElement.querySelector(
            '[data-oe-model="product.product"], [data-wsale-model="product.product"]'
        );
        return el ? parseInt(el.dataset.oeId || el.dataset.wsaleId) : null;
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
            this.ribbonOptions.isVariantMode(editingElement)
                ? editingElement.querySelector(".o_ribbons")?.dataset?.ribbonId
                : editingElement.querySelector(".o_ribbons")?.dataset?.templateRibbonId
        );
        const match = !ribbonId || !this.ribbonOptions.getRibbonsObject().hasOwnProperty(ribbonId)
            ? ''
            : ribbonId;
        return match === value;
    }
    apply({ isPreviewing, editingElement, value }) {
        const variantMode = this.ribbonOptions.isVariantMode(editingElement);
        if (variantMode) {
            const productVariantID = this.ribbonOptions.getProductVariantId(editingElement);
            this.ribbonOptions.addProductVariantsRibbons({
                recordId: productVariantID,
                ribbonId: value,
            });
        } else {
            const productTemplateID = parseInt(
                editingElement
                    .querySelector('[data-oe-model="product.template"]')
                    .getAttribute('data-oe-id')
            );
            this.ribbonOptions.addProductTemplatesRibbons({
                recordId: productTemplateID,
                ribbonId: value,
            });
        }

        const ribbon = this.ribbonOptions.getRibbonsObject()[value] || {
            id: '',
            name: '',
            bg_color: '',
            text_color: '',
            position: 'left',
            style: 'ribbon',
        };

        return this.ribbonOptions._setRibbon(
            editingElement,
            ribbon,
            !isPreviewing,
        );
    }
}
export class CreateRibbonAction extends BuilderAction {
    static id = 'createRibbon';
    static dependencies = ['productsRibbonOptionPlugin']
    setup() {
        this.ribbonOptions = this.dependencies.productsRibbonOptionPlugin
    }
    apply({ editingElement }) {
        const variantMode = this.ribbonOptions.isVariantMode(editingElement);
        const ribbonId = Date.now();
        if (variantMode) {
            const productVariantId = this.ribbonOptions.getProductVariantId(editingElement);
            this.ribbonOptions.addProductVariantsRibbons({
                recordId: productVariantId,
                ribbonId: ribbonId,
            });
        } else {
            const productTemplateId = parseInt(
                editingElement
                    .querySelector('[data-oe-model="product.template"]')
                    .getAttribute('data-oe-id')
            );
            this.ribbonOptions.addProductTemplatesRibbons({
                recordId: productTemplateId,
                ribbonId: ribbonId,
            });
        }

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
        return this.ribbonOptions._setRibbon(
            editingElement,
            ribbon,
            true,
        );
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
            this.ribbonOptions.isVariantMode(editingElement)
                ? editingElement.querySelector(".o_ribbons")?.dataset?.ribbonId
                : editingElement.querySelector(".o_ribbons")?.dataset?.templateRibbonId
        );
        if (!ribbonId || !this.ribbonOptions.getRibbonsObject().hasOwnProperty(ribbonId)) {
            return;
        }

        return this.ribbonOptions.getRibbonsObject()[ribbonId][params.mainParam];
    }
    isApplied({ editingElement, params, value }) {
        const ribbonId = parseInt(
            this.ribbonOptions.isVariantMode(editingElement)
                ? editingElement.querySelector(".o_ribbons")?.dataset?.ribbonId
                : editingElement.querySelector(".o_ribbons")?.dataset?.templateRibbonId
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
        const ribbonId = parseInt(
            this.ribbonOptions.isVariantMode(editingElement)
                ? ribbonEl.dataset.ribbonId
                : ribbonEl.dataset.templateRibbonId
        );
        const previousRibbon = this.ribbonOptions.getRibbonsObject()[ribbonId];
        this.ribbonOptions.setRibbonObject(ribbonId, {...previousRibbon, [setting]: value});
        this.ribbonOptions.setRibbon(ribbonId, {...previousRibbon, [setting]: value});
        const res = await this.ribbonOptions._setRibbon(
            editingElement,
            { ...previousRibbon, [setting]: value },
            !isPreviewMode,
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
