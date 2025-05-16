import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { ProductsItemOption } from "./products_item_option";
import { reactive } from "@odoo/owl";

class ProductsItemOptionPlugin extends Plugin {
    static id = "productsItemOptionPlugin";
    static dependencies = ["history"];
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

        builder_actions: this.getActions(),
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

    getActions() {
        const historyPlugin = this.dependencies.history;
        return {
            setItemSize: {
                reload: {},
                isApplied: ({ editingElement, value: [i, j] }) => {
                    if (
                        parseInt(editingElement.dataset.rowspan || 1) - 1 === i &&
                        parseInt(editingElement.dataset.colspan || 1) - 1 === j
                    ) {
                        this.itemSize.x = j + 1;
                        this.itemSize.y = i + 1;
                        return true;
                    }
                    return false;
                },

                apply: ({ editingElement, value: [i, j] }) => {
                    const x = j + 1;
                    const y = i + 1;

                    this.productTemplateID = parseInt(
                        editingElement
                            .querySelector('[data-oe-model="product.template"]')
                            .getAttribute("data-oe-id")
                    );
                    return rpc("/shop/config/product", {
                        product_id: this.productTemplateID,
                        x: x,
                        y: y,
                    });
                },
            },
            changeSequence: {
                reload: {},
                apply: ({ editingElement, value }) => {
                    this.productTemplateID = parseInt(
                        editingElement
                            .querySelector('[data-oe-model="product.template"]')
                            .getAttribute("data-oe-id")
                    );
                    return rpc("/shop/config/product", {
                        product_id: this.productTemplateID,
                        sequence: value,
                    });
                },
            },
            setRibbon: {
                isApplied: ({ editingElement, value }) =>
                    (parseInt(editingElement.dataset.ribbonId) || "") === value,
                apply: ({ editingElement, value }) => {
                    const isPreviewMode = historyPlugin.getIsPreviewing();
                    this.productTemplateID = parseInt(
                        editingElement
                            .querySelector('[data-oe-model="product.template"]')
                            .getAttribute("data-oe-id")
                    );
                    const ribbonId = value;
                    this.productTemplatesRibbons.push({
                        templateId: this.productTemplateID,
                        ribbonId: ribbonId,
                    });

                    const ribbon = this.ribbonsObject[ribbonId] || {
                        id: "",
                        name: "",
                        bg_color: "",
                        text_color: "",
                        position: "left",
                    };

                    return this._setRibbon(editingElement, ribbon, !isPreviewMode);
                },
            },
            createRibbon: {
                apply: ({ editingElement }) => {
                    this.productTemplateID = parseInt(
                        editingElement
                            .querySelector('[data-oe-model="product.template"]')
                            .getAttribute("data-oe-id")
                    );
                    const ribbonId = Date.now();
                    this.productTemplatesRibbons.push({
                        templateId: this.productTemplateID,
                        ribbonId: ribbonId,
                    });
                    const ribbon = reactive({
                        id: ribbonId,
                        name: "Ribbon Name",
                        bg_color: "",
                        text_color: "purple",
                        position: "left",
                    });
                    this.ribbons.push(ribbon);
                    this.ribbonsObject[ribbonId] = ribbon;
                    return this._setRibbon(editingElement, ribbon);
                },
            },
            modifyRibbon: {
                getValue: ({ editingElement, params }) => {
                    const field = params.mainParam;
                    const ribbonId = parseInt(editingElement.dataset.ribbonId);
                    if (!ribbonId) {
                        return;
                    }

                    return this.ribbonsObject[ribbonId][field];
                },
                isApplied: ({ editingElement, params, value }) => {
                    const field = params.mainParam;
                    let ribbonId = parseInt(editingElement.dataset.ribbonId);
                    if (!ribbonId) {
                        return;
                    }
                    if (!this.ribbonsObject[ribbonId]) {
                        ribbonId = Object.keys(this.ribbonsObject).find(
                            (key) => this.ribbonsObject[key].id === ribbonId
                        );
                        editingElement.dataset.ribbonId = ribbonId;
                    }
                    return this.ribbonsObject[ribbonId][field] === value;
                },
                apply: ({ editingElement, params, value }) => {
                    const isPreviewMode = historyPlugin.getIsPreviewing();
                    const setting = params.mainParam;
                    const ribbonId = parseInt(editingElement.dataset.ribbonId);
                    this.ribbonsObject[ribbonId][setting] = value;

                    const ribbon = this.ribbons.find((ribbon) => ribbon.id == ribbonId);
                    ribbon[setting] = value;

                    return this._setRibbon(editingElement, ribbon, !isPreviewMode);
                },
            },
            deleteRibbon: {
                apply: async ({ editingElement }) => {
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
                    return this._deleteRibbon(editingElement);
                },
            },
        };
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

        const proms = [];
        let createdRibbonIds;
        if (created.length > 0) {
            proms.push(
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

        for (const ribbon of modified) {
            const ribbonData = {
                name: ribbon.name,
                bg_color: ribbon.bg_color,
                text_color: ribbon.text_color,
                position: ribbon.position,
            };
            proms.push(this.services.orm.write("product.ribbon", [ribbon.id], ribbonData));
            this.originalRibbons[ribbon.id] = Object.assign({}, ribbon);
        }

        if (deletedIds.length > 0) {
            proms.push(this.services.orm.unlink("product.ribbon", deletedIds));
        }

        await Promise.all(proms);

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
            this.deletedRibbonClasses += ` ${
                this.ribbonPositionClasses[this.ribbonsObject[ribbonId].position]
            }`;

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
}

registry.category("website-plugins").add(ProductsItemOptionPlugin.id, ProductsItemOptionPlugin);
