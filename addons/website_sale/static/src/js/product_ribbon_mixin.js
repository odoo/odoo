import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { renderToElement } from "@web/core/utils/render";
import { _t } from "@web/core/l10n/translation";

export function productRibbonMixin(component) {
  return component.extend({
    async willStart() {
        const _super = this._super.bind(this);
        this.PositionClasses = {
            'ribbon': {'left': 'o_ribbon_left', 'right': 'o_ribbon_right'},
            'tag': {'left': 'o_tag_left', 'right': 'o_tag_right'},
        };
        this.ribbons = await new Promise((resolve) =>
            this.trigger_up('get_ribbons', { callback: resolve })
        );
        this.ribbon = this.$target.find('.o_ribbon')[0];
        this.ribbonEditMode = false;
        return _super(...arguments);
    },

    onfocus(){
        this._super(...arguments);
        // Ribbons may have been edited or deleted in another products' option, need to make sure
        // they're up to date
        this.rerender = true;
        this.ribbonEditMode = false;
    },

    _computeWidgetState(methodName, params){
        const classes = this.ribbon.className;
        switch(methodName){
            case 'setRibbon':
                return this.ribbon.dataset.ribbonId || '';
            case 'setRibbonName':
                return this.ribbon.textContent;
            case 'setRibbonPosition': {
                if (classes.includes('o_ribbon_left') || classes.includes('o_tag_left')){
                    return 'left';
                }
                return 'right';
            }
            case 'setRibbonStyle': {
                if (classes.includes('o_ribbon_right') || classes.includes('o_ribbon_left')){
                    return 'ribbon';
                }
                return 'tag';
            }
        }
        return this._super(...arguments);
    },

    async _computeWidgetVisibility(widgetName, params) {
        switch(widgetName){
            case 'create_ribbon_opt':
                return !this.ribbonEditMode;
            case 'edit_ribbon_opt':
                if(
                    this.ribbon.dataset.ribbonId
                    && this.ribbons.hasOwnProperty(this.ribbon.dataset.ribbonId)
                ){
                    return true;
                }
                return false;
        }
        return this._super(...arguments);
    },

    getPosition(className){
        return /(?:^|\s)(o_ribbon_left|o_tag_left)(?:\s|$)/.test(className)? 'left' : 'right';
    },

    getStyle(className){
        return /(?:^|\s)(o_ribbon_left|o_ribbon_right)(?:\s|$)/.test(className)? 'ribbon' : 'tag';
    },

    async setRibbon(previewMode, widgetValue, params) {
        if (previewMode === 'reset') {
            widgetValue = this.prevRibbonId;
        } else {
            this.prevRibbonId = this.ribbon.dataset.ribbonId;
            this.prevRibbon = {
                'name': this.ribbon.textContent,
                'position': this.getPosition(this.ribbon.className),
                'style': this.getStyle(this.ribbon.className),
                'bg_color': this.ribbon.style.backgroundColor,
                'text_color': this.ribbon.style.color,
            }
        }
        if (!previewMode) {
            this.ribbonEditMode = false;
        }
        await this._setRibbon(widgetValue);
    },

    /**
     * @see this.selectClass for params
     */
    editRibbon(previewMode, widgetValue, params) {
        this.ribbonEditMode = !this.ribbonEditMode;
    },

    /**
     * @see this.selectClass for params
     */
    async createRibbon(previewMode, widgetValue, params) {
        await this._setRibbon(false);
        this.ribbon.textContent = _t('Ribbon Name');
        this.ribbon.classList.add('o_ribbon_left');
        this.ribbonEditMode = true;
        await this._saveRibbon(true);
    },

    /**
     * @see this.selectClass for params
     */
    async deleteRibbon(previewMode, widgetValue, params) {
        const save = await new Promise(resolve => {
            this.dialog.add(ConfirmationDialog, {
                body: _t('Are you sure you want to delete this ribbon?'),
                confirm: () => resolve(true),
                cancel: () => resolve(false),
            });
        });
        if (!save) {
            return;
        }
        const ribbonId = this.ribbon.dataset.ribbonId;
        this.trigger_up('delete_ribbon', {id: ribbonId});
        this.ribbons = await new Promise((resolve) =>
            this.trigger_up("get_ribbons", { callback: resolve })
        );
        this.rerender = true;
        await this._setRibbon(ribbonId, true);
        this.ribbonEditMode = false;
    },
    /**
     * @see this.selectClass for params
     */
    async setRibbonName(previewMode, widgetValue, params) {
        this.ribbon.textContent = widgetValue.substring(0, 20); // The maximum length is 20.
        if (!previewMode) {
            await this._saveRibbon();
        }
    },
    /**
     * @see this.selectClass for params
     */

    async setRibbonPosition(previewMode, widgetValue, params) {
        const currentStyle = this.getStyle(this.ribbon.className);
        this.ribbon.className = this.ribbon.className.replace(
            /o_(ribbon|tag)_(left|right)/, this.PositionClasses[currentStyle][widgetValue]
        );
        await this._saveRibbon();
    },

    async setRibbonStyle(previewMode, widgetValue, params) {
        const currentPosition = this.getPosition(this.ribbon.className);
        this.ribbon.className = this.ribbon.className.replace(
            /o_(ribbon|tag)_(left|right)/, this.PositionClasses[widgetValue][currentPosition]
        );
        await this._saveRibbon();
    },

    /**
     * @override
     */
    async _renderCustomXML(uiFragment) {
        const select = uiFragment.querySelector('.o_wsale_ribbon_select');
        this.ribbons = await new Promise((resolve) =>
            this.trigger_up("get_ribbons", { callback: resolve })
        );
        const classes = this.ribbon.className;
        this.ribbon.className = '';
        const defaultTextColor = window.getComputedStyle(this.ribbon).color;
        this.ribbon.className = classes;
        Object.values(this.ribbons).forEach(ribbon => {
            select.append(renderToElement('website_sale.ribbonSelectItem', {
                ribbon,
                isLeft: ribbon.position === 'left',
                textColor: ribbon.text_color || defaultTextColor,
            }));
        });
    },

    /**
     * Saves the ribbons.
     *
     * @private
     * @param {Boolean} [isNewRibbon=false]
     */
    async _saveRibbon(isNewRibbon = false) {
        const text = this.ribbon.textContent.trim();
        const ribbon = {
            'name': text,
            'bg_color': this.ribbon.style.backgroundColor,
            'text_color': this.ribbon.style.color,
            'position': this.getPosition(this.ribbon.className),
            'style': this.getStyle(this.ribbon.className),
        };
        ribbon.id = isNewRibbon ? Date.now() : parseInt(this.ribbon.dataset.ribbonId);
        this.trigger_up('set_ribbon', {ribbon: ribbon});
        this.ribbons = await new Promise((resolve) =>
            this.trigger_up("get_ribbons", { callback: resolve })
        );
        this.rerender = true;
        await this._setRibbon(ribbon.id);
    },

    /**
     * Sets the ribbon.
     *
     * @private
     * @param {integer|false} ribbonId
     */
    async _setRibbon(ribbonId, del = false) {
        this.ribbon.dataset.ribbonId = ribbonId;
        this.trigger_up('set_product_ribbon', {
            templateId: this.productTemplateID,
            ribbonId: ribbonId || false,
        });

        let ribbon = {};
        if (del || !ribbonId) {
            // When ribbon is deleted or not set
            ribbon = { name: '', bg_color: '', text_color: '', position: 'left', style: 'ribbon' };
        } else {
            // When ribbon is set but ribbonId may not be in manually set ribbons
            ribbon = this.ribbons[ribbonId] || this.prevRibbon;
        }

        // Access the editable document content within an iframe
        const editableDocument = this.$target[0].ownerDocument.body;
        const ribbons = editableDocument.querySelectorAll(`[data-ribbon-id="${ribbonId}"]`);

        ribbons.forEach(ribbonElement => {
            ribbonElement.textContent = ribbon.name;
            const htmlClasses = ['o_tag_left', 'o_tag_right', 'o_ribbon_left', 'o_ribbon_right'];
            htmlClasses.forEach(cls => ribbonElement.classList.remove(cls));

            if (ribbon.style && ribbon.position) {
                ribbonElement.classList.add(this.PositionClasses[ribbon.style][ribbon.position]);
            }

            ribbonElement.style.backgroundColor = ribbon.bg_color;
            ribbonElement.style.color = ribbon.text_color;
        });

        if (del) {
            editableDocument.querySelectorAll(`[data-ribbon-id="${ribbonId}"]`).forEach(product => {
                delete product.dataset.ribbonId;
            }
        );
    }

    // Mark the ribbon as dirty to trigger a save process
    this.ribbon.classList.add('o_dirty');
    },

    updateUIVisibility: async function () {
        // TODO: update this once updateUIVisibility can be used to compute visibility
        // of arbitrary DOM elements and not just widgets.
        await this._super(...arguments);
        this.$el
            .find('[data-name="ribbon_customize_opt"]')
            .toggleClass("d-none", !this.ribbonEditMode);
    },

    /**
     * @override
     */
    async selectStyle(previewMode, widgetValue, params) {
        const proms = [this._super(...arguments)];
        if (params.cssProperty === 'background-color' && params.colorNames.includes(widgetValue)) {
            // Reset text-color when choosing a background-color class, so it uses the automatic
            // text-color of the class.
            proms.push(this.selectStyle(previewMode, '', {cssProperty: 'color'}));
        }
        await Promise.all(proms);
        if (!previewMode) {
            await this._saveRibbon();
        }
    },
  });
}
