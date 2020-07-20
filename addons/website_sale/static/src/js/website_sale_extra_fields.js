odoo.define('website_sale.add_product_template_field', function (require) {
'use strict';

const options = require('web_editor.snippets.options');
const {Class: EditorMenuBar} = require('web_editor.editor');
const {qweb} = require('web.core');

options.registry.ExtraProductFieldsSelect = options.Class.extend({
    xmlDependencies: (options.Class.prototype.xmlDependencies || []).concat(['/website_sale/static/src/xml/website_sale_utils.xml']),

    /**
     * @override
     */
    async willStart() {
        const _super = this._super.bind(this);
        this.addList = [];
        this.unlinkList = [];
        this.isEditing = false;
        this.trigger_up('context_get', {
            callback: (ctx) => {
                this.websiteId = ctx['website_id'];
            },
        });
        this.fieldIds = await this._rpc({
            model: 'ecom.extra.field',
            method: 'search_read',
            args: [[['website_id', '=', this.websiteId]], ['field_id', 'label']],
        });
        this.fieldIds = this.fieldIds.map(field => {
            return {
                id: field.id,
                field_id: {
                    id: field.field_id[0],
                    field_description: field.label,
                }
            }; 
        });
        this.productTemplateFields = await this._rpc({
            model: 'ir.model.fields',
            method: 'search_read',
            args: [[['model_id.model', '=', 'product.template']]],
        });
        this.availables = this.productTemplateFields.filter(field => {
            let available = true;
            this.fieldIds.forEach(extrafield => {
                if (extrafield.field_id.id === field.id) {
                    available = false;
                }
            }); 
            return available;
        });
        this.availables = this.availables.map(field => {
            return {
                id: 0,
                field_id: field,
            }; 
        });
        return _super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @see this.selectClass for params
     */
    addExtraField: function (previewMode, widgetValue, params) {
        const addedEntityId = parseInt(widgetValue);
        this.availables = this.availables.filter(field => {
            if (field.field_id.id === addedEntityId) {
                this.fieldIds.push(field);
                this.addList.push(field);
                return false;
            }
            return true;
        });
        this.rerender = true;
    },
    /**
     * @see this.selectClass for params
     */
    editExtraFieldList: function (previewMode, widgetValue, params) {
        this.isEditing = true;
        this._toggleEditUI();
        this._sendUpdateData();
        this.rerender = true;
    },
    /**
     * @see this.selectClass for params
     */
    removeExtraField: function (previewMode, widgetValue, params) {
        const removedEntityId = parseInt(widgetValue);
        this.unlinkList.push(widgetValue);
        this.fieldIds = this.fieldIds.filter(field => {
            if (field.field_id.id === removedEntityId) {
                this.unlinkList.push(field);
                this.availables.push(field);
                return false;
            }
            return true;
        });
        this.rerender = true;
    },
    saveExtraFieldList: function (previewMode, widgetValue, params) {
        this.isEditing = false;
        this._toggleEditUI();
        this._sendUpdateData();
        this.rerender = true;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    cleanForSave: function () {
        if (this.isEditing) {
            this._sendUpdateData();
        }
    },
    /**
     * @override
     */
    updateUI: async function () {
        await this._super.apply(this, arguments);

        if (this.rerender) {
            this.rerender = false;
            return this._rerenderXML();
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _renderCustomXML: async function (uiFragment) {
        this.$extraFieldList = $(uiFragment.querySelector('[data-name="extra_field_list"]'));
        this.$select = $(uiFragment.querySelector('[data-name="add_extra_field_opt"] we-select'));
        this.fieldIds.forEach(field => {
            this.$extraFieldList.append(qweb.render('website_sale.extraFieldListItem', {
                field: field.field_id,
                isEditing: this.isEditing,
            }));
        });
        this.availables.forEach(field => {
            this.$select.prepend(qweb.render('website_sale.extraFieldSelectItem', {
                field: field.field_id,
                isEditing: this.isEditing,
            }));
        });
    },
    /**
     * @private
     */
    _sendUpdateData: function () {
        this.trigger_up('set_record_update_data', {
            websiteId: this.websiteId,
            addList: this.addList,
            unlinkList: this.unlinkList,
        });
    },
    /**
     * @private
     */
    _toggleEditUI: function () {
        const $editMenu = $('[data-name="add_extra_field_opt"]');
        $editMenu.toggleClass('d-none', !this.isEditing);
        $('.o_we_edit_extra_field_btn').toggleClass('d-none', this.isEditing);
        $('.o_we_save_extra_field_btn').toggleClass('d-none', !this.isEditing);
    },
});

EditorMenuBar.include({
    custom_events: Object.assign(EditorMenuBar.prototype.custom_events, {
        set_record_update_data: '_onSetRecordUpdateData',
    }),
    /**
     * @override
     */
    async willStart() {
        const _super = this._super.bind(this);
        this.addList = [];
        this.unlinkList = [];
        return _super(...arguments);
    },
    /**
     * @override
     */
    async save() {
        const _super = this._super.bind(this);
        await _super(...arguments);
        this._saveChanges();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Saves changes in the database.
     *
     * @private
     */
    _saveChanges: function () {
        if (!this.addList && !this.unlinkList) {
            return;
        }
        const proms = [];
        this.addList.forEach(field => {
            proms.push(this._rpc({
                model: 'ecom.extra.field',
                method: 'create',
                args: [{
                    'website_id': this.websiteId,
                    'field_id': field.field_id.id
                }],
            }));
        });
        this.unlinkList.forEach(field => {
            proms.push(this._rpc({
                model: 'ecom.extra.field',
                method: 'unlink',
                args: [field.id],
            }));
        });
        return Promise.all(proms);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onSetRecordUpdateData: function (ev) {
        this.websiteId = ev.data.websiteId;
        this.addList = ev.data.addList;
        this.unlinkList = ev.data.unlinkList;
    },
});
});
