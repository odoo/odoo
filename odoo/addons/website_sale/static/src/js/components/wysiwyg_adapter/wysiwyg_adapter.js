/** @odoo-module **/

import { WysiwygAdapterComponent } from '@website/components/wysiwyg_adapter/wysiwyg_adapter';
import { patch } from "@web/core/utils/patch";
import { markup } from "@odoo/owl";

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
                ['id', 'html', 'bg_color', 'text_color', 'html_class'],
            );
        }
        this.ribbons = Object.fromEntries(ribbons.map(ribbon => {
            ribbon.html = markup(ribbon.html);
            return [ribbon.id, ribbon];
        }));
        this.originalRibbons = Object.assign({}, this.ribbons);
        this.productTemplatesRibbons = [];
        this.deletedRibbonClasses = '';
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

    /**
     * Returns a copy of this.ribbons through a callback.
     *
     * @private
     */
    _onGetRibbons(ev) {
        ev.data.callback(Object.assign({}, this.ribbons));
    },
    /**
     * Returns all ribbon classes, current and deleted, so they can be removed.
     *
     * @private
     */
    _onGetRibbonClasses(ev) {
        const classes = Object.values(this.ribbons).reduce((classes, ribbon) => {
            return classes + ` ${ribbon.html_class}`;
        }, '') + this.deletedRibbonClasses;
        ev.data.callback(classes);
    },
    /**
     * Deletes a ribbon.
     *
     * @private
     */
    _onDeleteRibbon(ev) {
        this.deletedRibbonClasses += ` ${this.ribbons[ev.data.id].html_class}`;
        delete this.ribbons[ev.data.id];
    },
    /**
     * Sets a ribbon;
     *
     * @private
     */
    _onSetRibbon(ev) {
        const {ribbon} = ev.data;
        const previousRibbon = this.ribbons[ribbon.id];
        if (previousRibbon) {
            this.deletedRibbonClasses += ` ${previousRibbon.html_class}`;
        }
        this.ribbons[ribbon.id] = ribbon;
    },
    /**
     * Sets which ribbon is used by a product template.
     *
     * @private
     */
    _onSetProductRibbon(ev) {
        const {templateId, ribbonId} = ev.data;
        this.productTemplatesRibbons.push({templateId, ribbonId});
    },
    /**
     * @override
     */
    _trigger_up(ev) {
        const methods = {
            get_ribbons: this._onGetRibbons.bind(this),
            get_ribbon_classes: this._onGetRibbonClasses.bind(this),
            delete_ribbon: this._onDeleteRibbon.bind(this),
            set_ribbon: this._onSetRibbon.bind(this),
            set_product_ribbon: this._onSetProductRibbon.bind(this),
        }
        if (methods[ev.name]) {
            return methods[ev.name](ev);
        } else {
            return super._trigger_up(...arguments);
        }
    },
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
