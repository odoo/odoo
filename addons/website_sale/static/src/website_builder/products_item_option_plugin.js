import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { ProductsItemOption } from "./products_item_option";
import { reactive } from "@odoo/owl";
import { BuilderAction } from "@html_builder/core/builder_action";

class ProductsItemOptionPlugin extends Plugin {
    static id = "productsItemOptionPlugin";
    static shared = [
        "setItemSize",
        "setProductTemplateID",
        "getProductTemplateID",
        "addProductTemplatesRibbons",
        "getRibbonsObject",
        "setRibbonObject",
        "addRibbon",
        "getRibbons",
        "_deleteRibbon",
        "_setRibbon"
    ];
    itemSize = reactive({ x: 1, y: 1 });
    count = reactive({ value: 0 });


    resources = {
        builder_options: [
            {
                OptionComponent: ProductsItemOption,
                props: {
                    loadInfo: this.loadInfo.bind(this),
                    itemSize: this.itemSize,
                    count: this.count,
                },
                selector: "#products_grid .oe_product",
                editableOnly: false,
                title: _t("Product"),
                groups: ["website.group_website_designer"],
            },
        ],

        builder_actions: {
            SetItemSizeAction,
            ChangeSequenceAction,
            SetRibbonAction,
            CreateRibbonAction,
            ModifyRibbonAction,
            DeleteRibbonAction,
        },
    };

    setup() {
        this.currentWebsiteId = this.services.website.currentWebsiteId;
        this.ribbonPositionClasses = {
            left: "o_ribbon_left",
            right: "o_ribbon_right",
        };

        this.productTemplatesRibbons = [];
        this.deletedRibbonClasses = "";
        this.editMode = false;
    }

    async loadInfo() {
        [this.ribbons, this.defaultSort] = await Promise.all([
            this.loadRibbons(),
            this.getDefaultSort(),
        ]);

        this.ribbonsObject = {};
        for (const ribbon of this.ribbons) {
            this.ribbonsObject[ribbon.id] = ribbon;
        }

        this.originalRibbons = JSON.parse(JSON.stringify(this.ribbonsObject));

        return [this.ribbons, this.defaultSort];
    }

    async loadRibbons() {
        return (
            this.ribbons ||
            reactive(
                await this.services.orm.searchRead(
                    "product.ribbon",
                    [],
                    ["id", "name", "bg_color", "text_color", "position"]
                )
            )
        );
    }

    async getDefaultSort() {
        return (
            this.defaultSort ||
            (await this.services.orm.searchRead(
                "website",
                [["id", "=", this.currentWebsiteId]],
                ["shop_default_sort"]
            ))
        );
    }

    _setRibbon(editingElement, ribbon, save = true) {
        const ribbonId = ribbon.id;
        const editableBody = editingElement.ownerDocument.body;
        editingElement.dataset.ribbonId = ribbonId;

        // Find or create ribbon element
        let ribbonElement = editingElement.querySelector(".o_ribbon");
        if (!ribbonElement && ribbonId) {
            ribbonElement = this.document.createElement("span");
            ribbonElement.classList.add("o_ribbon o_ribbon_left");
            editingElement.appendChild(ribbonElement);
        }

        // Update all ribbons with this ID
        const ribbons = editableBody.querySelectorAll(`[data-ribbon-id="${ribbonId}"] .o_ribbon`);

        for (const ribbonElement of ribbons) {
            ribbonElement.textContent = "";
            ribbonElement.textContent = ribbon.name;

            const htmlClasses = this._getRibbonClasses();
            ribbonElement.classList.remove(...htmlClasses.trim().split(" "));

            if (ribbonElement.classList.contains("d-none")) {
                ribbonElement.classList.remove("d-none");
            }

            ribbonElement.classList.add(this.ribbonPositionClasses[ribbon.position]);
            ribbonElement.style.backgroundColor = ribbon.bg_color || "";
            ribbonElement.style.color = ribbon.text_color || "";
        }

        return save ? this._saveRibbons() : "";
    }
    /**
     * Returns all ribbon classes, current and deleted, so they can be removed.
     *
     */
    _getRibbonClasses() {
        const ribbonClasses = [];
        for (const ribbon of Object.values(this.ribbons)) {
            ribbonClasses.push(this.ribbonPositionClasses[ribbon.position]);
        }
        return ribbonClasses.join(" ") + " " + this.deletedRibbonClasses;
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
        let createdRibbonIds;
        if (created.length > 0) {
            createdRibbonProms.push(
                this.services.orm
                    .create(
                        "product.ribbon",
                        created.map((ribbon) => {
                            ribbon = Object.assign({}, ribbon);
                            this.originalRibbons[ribbon.id] = ribbon;
                            delete ribbon.id;
                            return ribbon;
                        })
                    )
                    .then((ids) => (createdRibbonIds = ids))
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
            };
            const serverId = localToServer[ribbon.id]?.id || ribbon.id;
            proms.push(this.services.orm.write("product.ribbon", [serverId], ribbonData));
            this.originalRibbons[ribbon.id] = Object.assign({}, ribbon);
        }

        if (deletedIds.length > 0) {
            proms.push(this.services.orm.unlink("product.ribbon", deletedIds));
        }

        await Promise.all(proms);

        // Building the final template to ribbon-id map
        const finalTemplateRibbons = this.productTemplatesRibbons.reduce(
            (acc, { templateId, ribbonId }) => {
                acc[templateId] = ribbonId;
                return acc;
            },
            {}
        );
        // Inverting the relationship so that we have all templates that have the same ribbon to reduce RPCs
        const ribbonTemplates = {};
        for (const templateId in finalTemplateRibbons) {
            const ribbonId = finalTemplateRibbons[templateId];
            if (!ribbonTemplates[ribbonId]) {
                ribbonTemplates[ribbonId] = [];
            }
            ribbonTemplates[ribbonId].push(parseInt(templateId));
        }

        const promises = [];
        for (const ribbonId in ribbonTemplates) {
            const templateIds = ribbonTemplates[ribbonId];
            const parsedId = parseInt(ribbonId);
            const validRibbonId = currentIds.includes(parsedId) ? ribbonId : false;
            promises.push(
                this.services.orm.write("product.template", templateIds, {
                    website_ribbon_id: localToServer[validRibbonId]?.id || false,
                })
            );
        }

        return Promise.all(promises);
    }

    /**
     * Deletes a ribbon.
     *
     */
    _deleteRibbon(editingElement) {
        const ribbonId = parseInt(editingElement.dataset.ribbonId);
        if (this.ribbonsObject[ribbonId]) {
            this.deletedRibbonClasses += `${
                this.ribbonPositionClasses[this.ribbonsObject[ribbonId].position]
            } `;

            const ribbonIndex = this.ribbons.indexOf(
                this.ribbons.find((ribbon) => ribbon.id === ribbonId)
            );
            if (ribbonIndex >= 0) {
                this.ribbons.splice(ribbonIndex, 1);
            }
            delete this.ribbonsObject[ribbonId];

            // update "reactive" count to trigger rerendering the BuilderSelect component (which has the value as a t-key)
            this.count.value++;
        }

        this.productTemplateID = parseInt(
            editingElement
                .querySelector('[data-oe-model="product.template"]')
                .getAttribute("data-oe-id")
        );
        editingElement.dataset.ribbonId = "";
        this.productTemplatesRibbons.push({
            templateId: this.productTemplateID,
            ribbonId: false,
        });

        const ribbonElement = editingElement.querySelector(".o_ribbon");
        if (ribbonElement) {
            ribbonElement.classList.add("d-none");
        }
        this._saveRibbons();
    }
    setItemSize(x, y) {
        this.itemSize.x = x;
        this.itemSize.y = y;
    }
    setProductTemplateID(value) {
        this.productTemplateID = value;
    }
    getProductTemplateID() {
        return this.productTemplateID;
    }
    addProductTemplatesRibbons(value) {
        this.productTemplatesRibbons.push(value);
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

}

export class SetItemSizeAction extends BuilderAction {
    static id = "setItemSize";
    static dependencies = ["productsItemOptionPlugin"];
    setup() {
        this.reload = {};
    }
    isApplied({ editingElement, value: [i, j] }) {
        if (
            parseInt(editingElement.dataset.rowspan || 1) - 1 === i &&
            parseInt(editingElement.dataset.colspan || 1) - 1 === j
        ) {
            this.dependencies.productsItemOptionPlugin.setItemSize(j + 1, i + 1);
            return true;
        }
        return false;
    }
    apply({ editingElement, value: [i, j] }) {
        const x = j + 1;
        const y = i + 1;

        this.dependencies.productsItemOptionPlugin.setProductTemplateID(parseInt(
            editingElement
                .querySelector('[data-oe-model="product.template"]')
                .getAttribute("data-oe-id")
        ));
        return rpc("/shop/config/product", {
            product_id: this.dependencies.productsItemOptionPlugin.getProductTemplateID(),
            x: x,
            y: y,
        });
    }
}
export class ChangeSequenceAction extends BuilderAction {
    static id = "changeSequence";
    static dependencies = ["productsItemOptionPlugin"];
    setup() {
        this.reload = {};
    }
    apply({ editingElement, value }) {
        this.dependencies.productsItemOptionPlugin.setProductTemplateID(parseInt(
            editingElement
                .querySelector('[data-oe-model="product.template"]')
                .getAttribute("data-oe-id")
        ));
        return rpc("/shop/config/product", {
            product_id: this.dependencies.productsItemOptionPlugin.getProductTemplateID(),
            sequence: value,
        });
    }
}
export class SetRibbonAction extends BuilderAction {
    static id = "setRibbon";
    static dependencies = ["productsItemOptionPlugin"];
    isApplied({ editingElement, value }) {
        return (parseInt(editingElement.dataset.ribbonId) || "") === value;
    }
    apply({ isPreviewing, editingElement, value }) {
        this.dependencies.productsItemOptionPlugin.setProductTemplateID(parseInt(
            editingElement
                .querySelector('[data-oe-model="product.template"]')
                .getAttribute("data-oe-id")
        ));
        const ribbonId = value;
        this.dependencies.productsItemOptionPlugin.addProductTemplatesRibbons({
            templateId: this.dependencies.productsItemOptionPlugin.getProductTemplateID(),
            ribbonId: ribbonId,
        });

        const ribbon = this.dependencies.productsItemOptionPlugin.getRibbonsObject()[ribbonId] || {
            id: "",
            name: "",
            bg_color: "",
            text_color: "",
            position: "left",
        };

        return this.dependencies.productsItemOptionPlugin._setRibbon(editingElement, ribbon, !isPreviewing);
    }
}
export class CreateRibbonAction extends BuilderAction {
    static id = "createRibbon";
    dependencies = ["productsItemOptionPlugin"]
    apply({ editingElement }) {
        this.dependencies.productsItemOptionPlugin.setProductTemplateID(parseInt(
            editingElement
                .querySelector('[data-oe-model="product.template"]')
                .getAttribute("data-oe-id")
        ));
        const ribbonId = Date.now();
        this.dependencies.productsItemOptionPlugin.addProductTemplatesRibbons({
            templateId: this.dependencies.productsItemOptionPlugin.getProductTemplateID(),
            ribbonId: ribbonId,
        });
        const ribbon = reactive({
            id: ribbonId,
            name: "Ribbon Name",
            bg_color: "",
            text_color: "purple",
            position: "left",
        });
        this.dependencies.productsItemOptionPlugin.addRibbon(ribbon);
        this.dependencies.productsItemOptionPlugin.setRibbonObject(ribbonId, ribbon);
        return this.dependencies.productsItemOptionPlugin._setRibbon(editingElement, ribbon);
    }
}
export class ModifyRibbonAction extends BuilderAction {
    static id = "modifyRibbon";
    static dependencies = ["productsItemOptionPlugin"];
    setup() {
        this.piop = this.dependencies.productsItemOptionPlugin
    }
    getValue({ editingElement, params }) {
        const field = params.mainParam;
        const ribbonId = parseInt(editingElement.dataset.ribbonId);
        if (!ribbonId) {
            return;
        }

        return this.dependencies.productsItemOptionPlugin.getRibbonsObject()[ribbonId][field];
    }
    isApplied({ editingElement, params, value }) {
        const field = params.mainParam;
        let ribbonId = parseInt(editingElement.dataset.ribbonId);
        if (!ribbonId) {
            return;
        }
        if (!this.dependencies.productsItemOptionPlugin.getRibbonsObject()[ribbonId]) {
            ribbonId = Object.keys(this.dependencies.productsItemOptionPlugin.getRibbonsObject()).find(
                (key) => this.dependencies.productsItemOptionPlugin.getRibbonsObject()[key].id === ribbonId
            );
            editingElement.dataset.ribbonId = ribbonId;
        }
        return this.dependencies.productsItemOptionPlugin.getRibbonsObject()[ribbonId][field] === value;
    }
    apply({ isPreviewing, editingElement, params, value }) {
        const setting = params.mainParam;
        const ribbonId = parseInt(editingElement.dataset.ribbonId);
        this.dependencies.productsItemOptionPlugin.getRibbonsObject()[ribbonId][setting] = value;

        const ribbon = this.dependencies.productsItemOptionPlugin.getRibbons().find((ribbon) => ribbon.id == ribbonId);
        ribbon[setting] = value;

        return this.plugin._setRibbon(editingElement, ribbon, !isPreviewing);
    }
}
export class DeleteRibbonAction extends BuilderAction {
    static id = "deleteRibbon";
    static dependencies = ["productsItemOptionPlugin"];
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
        return this.dependencies.productsItemOptionPlugin._deleteRibbon(editingElement);
    }
}

registry.category("website-plugins").add(ProductsItemOptionPlugin.id, ProductsItemOptionPlugin);
