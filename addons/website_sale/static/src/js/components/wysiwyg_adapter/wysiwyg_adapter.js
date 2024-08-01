/** @odoo-module **/

import { WysiwygAdapterComponent } from '@website/components/wysiwyg_adapter/wysiwyg_adapter';
import { patch } from "@web/core/utils/patch";

patch(WysiwygAdapterComponent.prototype, {
    /**
     * @override
     */
    async init() {
        await super.init(...arguments);

        let ribbons = [];
        if (this._isProductListPage()) {
            ribbons = await this.orm.searchRead(
                'product.ribbon',
                [],
                ['id', 'name', 'bg_color', 'text_color', 'position'],
            );
        }
        this.ribbons = Object.fromEntries(ribbons.map(ribbon => {
            return [ribbon.id, ribbon];
        }));
        this.originalRibbons = Object.assign({}, this.ribbons);
        this.productTemplatesRibbons = [];
        this.deletedRibbonClasses = '';
        this.ribbonPositionClasses = {'left': 'o_ribbon_left', 'right': 'o_ribbon_right'};
    },
    /**
     * Returns a copy of this.ribbons.
     */
    getRibbons() {
        return Object.assign({}, this.ribbons);
    },
    /**
     * Returns all ribbon classes, current and deleted, so they can be removed.
     */
    getRibbonClasses() {
        return Object.values(this.ribbons).reduce((classes, ribbon) => {
            return classes + ` ${this.ribbonPositionClasses[ribbon.position]}`;
        }, '') + this.deletedRibbonClasses;
    },
    /**
     * Deletes a ribbon.
     *
     * @param {number} id - The id of the ribbon to delete.
     */
    deleteRibbon(id) {
        this.deletedRibbonClasses += ` ${
            this.ribbonPositionClasses[this.ribbons[id].position]
        }`;
        delete this.ribbons[id];
    },
    /**
     * Sets a ribbon.
     *
     * @param {Object} ribbon
     * @property {number} ribbon.id
     */
    setRibbon(ribbon) {
        const previousRibbon = this.ribbons[ribbon.id];
        if (previousRibbon) {
            this.deletedRibbonClasses += ` ${this.ribbonPositionClasses[previousRibbon.position]}`;
        }
        this.ribbons[ribbon.id] = ribbon;
    },
    /**
     * Sets which ribbon is used by a product template.
     *
     * @param {number} templateId - The product template's id.
     * @param {number|false} ribbonId - The ribbon's id.
     */
    setProductRibbon(templateId, ribbonId) {
        this.productTemplatesRibbons.push({templateId, ribbonId});
    },
    /**
     * @override
     */
    async _saveViewBlocks() {
        await this._saveRibbons();
        return super._saveViewBlocks(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Saves the ribbons in the database.
     *
     * @private
     */
    async _saveRibbons() {
        if (!this._isProductListPage()) {
            return;
        }
        const originalIds = Object.keys(this.originalRibbons).map(id => parseInt(id));
        const currentIds = Object.keys(this.ribbons).map(id => parseInt(id));

        const ribbons = Object.values(this.ribbons);
        const created = ribbons.filter(ribbon => !originalIds.includes(ribbon.id));
        const deletedIds = originalIds.filter(id => !currentIds.includes(id));
        const modified = ribbons.filter(ribbon => {
            if (created.includes(ribbon)) {
                return false;
            }
            const original = this.originalRibbons[ribbon.id];
            return Object.entries(ribbon).some(([key, value]) => value !== original[key]);
        });

        const proms = [];
        let createdRibbonIds;
        if (created.length > 0) {
            proms.push(this.orm.create(
                'product.ribbon',
                created.map(ribbon => {
                    ribbon = Object.assign({}, ribbon);
                    delete ribbon.id;
                    return ribbon;
                }),
            ).then(ids => createdRibbonIds = ids));
        }

        modified.forEach(ribbon => proms.push(this.orm.write(
            'product.ribbon',
            [ribbon.id],
            ribbon,
        )));

        if (deletedIds.length > 0) {
            proms.push(this.orm.unlink(
                'product.ribbon',
                deletedIds,
            ));
        }
        await Promise.all(proms);
        const localToServer = Object.assign(
            this.ribbons,
            Object.fromEntries(created.map((ribbon, index) => [ribbon.id, {id: createdRibbonIds[index]}])),
            {'false': {id: false}},
        );

        // Building the final template to ribbon-id map
        const finalTemplateRibbons = this.productTemplatesRibbons.reduce((acc, {templateId, ribbonId}) => {
            acc[templateId] = ribbonId;
            return acc;
        }, {});
        // Inverting the relationship so that we have all templates that have the same ribbon to reduce RPCs
        const ribbonTemplates = Object.entries(finalTemplateRibbons).reduce((acc, [templateId, ribbonId]) => {
            if (!acc[ribbonId]) {
                acc[ribbonId] = [];
            }
            acc[ribbonId].push(parseInt(templateId));
            return acc;
        }, {});
        const setProductTemplateRibbons = Object.entries(ribbonTemplates)
            // If the ribbonId that the template had no longer exists, remove the ribbon (id = false)
            .map(([ribbonId, templateIds]) => {
                const id = currentIds.includes(parseInt(ribbonId)) ? ribbonId : false;
                return [id, templateIds];
            }).map(([ribbonId, templateIds]) => this.orm.write(
                'product.template',
                templateIds,
                {'website_ribbon_id': localToServer[ribbonId].id},
            ));
        return Promise.all(setProductTemplateRibbons);
    },
    /**
     * Checks whether the current page is the product list.
     *
     * @private
     */
    _isProductListPage() {
        return this.options.editable && this.options.editable.find('#products_grid').length !== 0;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    // TODO this whole patch actually seems unnecessary. The bug it solved seems
    // to stay solved if this is removed. To investigate.
    /**
     * @override
     */
     _getContentEditableAreas() {
        const array = super._getContentEditableAreas(...arguments);
        return array.filter(el => {
            // TODO should really review this system of "ContentEditableAreas +
            // ReadOnlyAreas", here the "products_header" stuff is duplicated in
            // both but this system is also duplicated with o_not_editable and
            // maybe even other systems (like preserving contenteditable="false"
            // with oe-keep-contenteditable).
            return !el.closest('.oe_website_sale .products_header');
        });
    },
    /**
     * @override
     */
    _getReadOnlyAreas() {
        const readOnlyEls = super._getReadOnlyAreas(...arguments);
        return [...readOnlyEls].concat(
            $(this.websiteService.pageDocument).find("#wrapwrap").find('.oe_website_sale .products_header, .oe_website_sale .products_header a').toArray()
        );
    },
});
