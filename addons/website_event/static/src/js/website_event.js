import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.WebsiteEventLayout = publicWidget.Widget.extend({
    selector: '.o_wevent_index',
    disabledInEditableMode: false,
    events: {
        'change .o_wevent_apply_layout input': '_onApplyEventLayoutChange',
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onApplyEventLayoutChange: async function (ev) {
        const wysiwyg = this.options.wysiwyg;
        if (wysiwyg) {
            wysiwyg.odooEditor.observerUnactive('_onApplyEventLayoutChange');
        }
        var clickedValue = ev.target.value;
        if (!this.editableMode) {
            await rpc('/event/save_event_layout_mode', {
                'layout_mode': clickedValue,
            });
        }

        // Update btn-group state
        document.querySelector('input.o_wevent_apply_grid').checked = (clickedValue === 'grid');
        document.querySelector('input.o_wevent_apply_list').checked = (clickedValue === 'list');
        document.querySelector('label.o_wevent_apply_grid').classList.toggle('active')
        document.querySelector('label.o_wevent_apply_list').classList.toggle('active')

        // Update layout
        document.querySelector('.o_wevent_event_grid_layout').classList.toggle('d-none');
        document.querySelector('.o_wevent_event_list_layout').classList.toggle('d-none');

        if (wysiwyg) {
            wysiwyg.odooEditor.observerActive('_onApplyEventLayoutChange');
        }
    },
});
