import { BuilderAction } from "@html_builder/core/builder_action";
import { SNIPPET_SPECIFIC_NEXT } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { reactive } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { ProductsRibbonOption } from "./product_ribbon_options";

export class ProductHeaderShopOption2 extends ProductsRibbonOption {
    static name = 'ProductsRibbonOption';
    static selector = "#products_grid .oe_product";
    static editableOnly = false;
    static groups = ['website.group_website_designer'];
}

class ProductsRibbonOptionPlugin extends Plugin {
    static id = 'productsRibbonOptionPlugin';
    static dependencies = ['history'];
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
        'loadInfo',
        'getCount',
    ];
    count = reactive({ value: 0 });

    resources = {
        builder_options: [
            withSequence(SNIPPET_SPECIFIC_NEXT, ProductHeaderShopOption2),
        ],
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
        this.editMode = false;
        this.localIdToServerId = {};
    }
    getCount() {
        return this.count;
    }

    async loadInfo() {
        if (!this.ribbons) {
            const result = await this.services.orm.searchRead(
                'product.ribbon',
                [['assign', '=', 'manual']],
                ['id', 'name', 'bg_color', 'text_color', 'position', 'style']
            );
            this.ribbons = reactive(result);
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
                    created.map((ribbon) => {
                        ribbon = Object.assign({}, ribbon);
                        delete ribbon.id;
                        return ribbon;
                    })
                ).then((ids) => {
                    // Map each created ribbon's local ID to its server ID
                    created.forEach((ribbon, index) => {
                        this.localIdToServerId[ribbon.id] = ids[index];
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
            const serverId = this.localIdToServerId[ribbon.id] || ribbon.id;
            proms.push(this.services.orm.write('product.ribbon', [serverId], ribbonData));
            this.originalRibbons[ribbon.id] = Object.assign({}, ribbon);
        }

        if (deletedIds.length > 0) {
            const serverIds = deletedIds.map((id) => this.localIdToServerId?.[id] || id);
            proms.push(this.services.orm.unlink("product.ribbon", serverIds));
        }

        await Promise.all(proms);

        // Building the final template to ribbon-id map so that we can remove duplicate entries
        const finalTemplateRibbons = this.productTemplatesRibbons.reduce(
            (acc, { templateId, ribbonId }) => {
                acc[templateId] = ribbonId;
                return acc;
            }, {},
        );
        // Inverting the relationship so that we have all templates that have the same ribbon to
        // reduce RPCs
        const ribbonTemplates = {};
        for (const [templateId, ribbonId] of Object.entries(finalTemplateRibbons)) {
            const serverRibbonId = this.localIdToServerId[ribbonId] ?? ribbonId;
            const templates = (ribbonTemplates[serverRibbonId] ||= []);
            templates.push(parseInt(templateId));
        }

        const promises = [];
        for (const [ribbonIdStr, templateIds] of Object.entries(ribbonTemplates)) {
            const ribbonId = parseInt(ribbonIdStr) || false;
            promises.push(
                this.services.orm.write("product.template", templateIds, {
                    website_ribbon_id: ribbonId,
                })
            );
        }

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
            let templateId;
            if (isProductPage) {
                templateId = this.productTemplateID;
            } else {
                // Find the product template ID from the ribbon element's parent form
                const productForm = ribbonElement.closest('form.oe_product_cart');
                const templateElement = productForm?.querySelector('[data-oe-model="product.template"]');
                templateId = templateElement ? parseInt(templateElement.getAttribute('data-oe-id')) : null;
            }
            if (templateId && !isNaN(templateId)) {
                this.productTemplatesRibbons = this.productTemplatesRibbons.filter(
                    (entry) => entry.templateId !== templateId
                );
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
     * @param {number} templateId - Product template ID
     * @param {number|string} ribbonId - Ribbon ID to assign
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

class SetRibbonAction extends BuilderAction {
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
        const productTemplateID = parseInt(
            editingElement
                .querySelector('[data-oe-model="product.template"]')
                .getAttribute('data-oe-id')
        );
        this.ribbonOptions.setProductTemplateID(productTemplateID)
        this.ribbonOptions.addProductTemplatesRibbons({
            templateId: productTemplateID,
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
class CreateRibbonAction extends BuilderAction {
    static id = 'createRibbon';
    static dependencies = ['productsRibbonOptionPlugin']
    setup(){
        this.ribbonOptions = this.dependencies.productsRibbonOptionPlugin
    }
    apply({ editingElement }) {
        const productTemplateId = parseInt(
            editingElement
                .querySelector('[data-oe-model="product.template"]')
                .getAttribute("data-oe-id")
        );
        this.ribbonOptions.setProductTemplateID(productTemplateId);
        const ribbonId = Date.now();
        this.ribbonOptions.addProductTemplatesRibbons({
            templateId: productTemplateId,
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
class ModifyRibbonAction extends BuilderAction {
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
        this.ribbonOptions.setRibbonObject(ribbonId, { ...previousRibbon, [setting]: value });
        this.ribbonOptions.setRibbon(ribbonId, { ...previousRibbon, [setting]: value });
        const res = await this.ribbonOptions._setRibbon(
            ribbonEl,
            { ...previousRibbon, [setting]: value },
            !isPreviewMode
        );
        if(isPreviewMode){
            this.ribbonOptions.setRibbonObject(ribbonId, previousRibbon);
            this.ribbonOptions.setRibbon(ribbonId, previousRibbon);
        }
        return res;
    }
}
class DeleteRibbonAction extends BuilderAction {
    static id = 'deleteRibbon';
    static dependencies = ['productsRibbonOptionPlugin'];
    setup() {
        this.canTimeout = false;
    }
    async apply({ editingElement }) {
        const save = await new Promise((resolve) => {
            this.services.dialog.add(ConfirmationDialog, {
                body: _t("Are you sure you want to delete this ribbon?"),
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
