/** @odoo-module **/

import publicWidget from 'web.public.widget';
import Dialog from 'web.Dialog';
import { _t } from 'web.core';

const categoryDeleteDialog = Dialog.extend({
    template: 'slides.category.delete',

    /**
     * @constructor
     * @param {Widget} parent
     * @param {DOM Object} slideTarget
     */
    init(parent, slideTarget) {
        this.categoryId = parseInt(slideTarget.dataset.categoryId);
        this._super(parent, {
            title: _t('Delete Category'),
            size: 'medium',
            buttons: [{
                text: _t('Delete'),
                classes: 'btn-primary',
                click: () => this._onClickDelete(),
            }, {
                text: _t('Cancel'),
                close: true
            }]
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Calls 'unlink' method on slides.slide to delete the category and
     * reloads page after deletion to re-arrange the content on UI
     *
     * @private
     */
    _onClickDelete() {
        this._rpc({
            model: 'slide.slide',
            method: 'unlink',
            args: [this.categoryId],
        }).then(function () {
            window.location.reload();
        });
    }
});

publicWidget.registry.websiteSlidesCategoryDelete = publicWidget.Widget.extend({
    selector: '.o_wslides_js_category_delete',
    xmlDependencies: ['/website_slides/static/src/xml/slide_management.xml'],
    events: {
        'click': '_onClickDeleteCateogry',
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickDeleteCateogry(ev) {
        new categoryDeleteDialog(this, ev.currentTarget).open();
    },
});

export default {
    categoryDeleteDialog: categoryDeleteDialog,
    websiteSlidesCategoryDelete: publicWidget.registry.websiteSlidesCategoryDelete
};
