/** @odoo-module **/

import Widget from 'web.Widget';

const SelectOptionsPopoverWidget = Widget.extend({
    template: 'wysiwyg.widgets.selectoptions.edit.tooltip',
    xmlDependencies: ['/web_editor/static/src/xml/wysiwyg.xml'],
    events: {
        'click .o_we_remove_select': '_onRemoveSelectClick',
        'click .o_we_edit_select': '_onEditSelectClick',
    },

    /**
     * @constructor
     * @param {Element} target: target Element for which we display a popover
     * @param {OdooClass} wysiwyg
     */
    init(parent, target, wysiwyg) {
        this._super(...arguments);
        this.target = target;
        this.$target = $(target);
        this.wysiwyg = wysiwyg
    },
    /**
     * @override
     */
    start() {
        this.$target.popover({
            html: true,
            delay: 2000,
            content: this.$el,
            placement: 'auto',
            trigger: 'click',
        })
        .popover('show')
        .data('bs.popover').tip.classList.add('o_edit_select_popover');

        return this._super(...arguments);
    },
    /**
     * @override
     */
    destroy() {
        this.$target.popover('dispose');
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Opens the Select Options Dialog.
     *
     * @private
     * @param {Event} ev
     */
    _onEditSelectClick(ev) {
        this.wysiwyg.openSelectOptionsDialog(this.target);
        ev.preventDefault();
        ev.stopImmediatePropagation();
        this.destroy();
    },
    /**
     * Removes the select element.
     *
     * @private
     * @param {Event} ev
     */
    _onRemoveSelectClick(ev) {
        ev.preventDefault();
        ev.stopImmediatePropagation();
        this.destroy();
        this.$target.remove();
    },
});

export default SelectOptionsPopoverWidget;
