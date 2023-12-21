/** @odoo-module **/

import { CourseTagAddDialog } from "@website_slides/js/public/components/course_tag_add_dialog/course_tag_add_dialog";
import publicWidget from '@web/legacy/js/public/public_widget';

publicWidget.registry.websiteSlidesTag = publicWidget.Widget.extend({
    selector: '.o_wslides_js_channel_tag_add',
    events: {
        'click': '_onAddTagClick',
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onAddTagClick: function (ev) {
        ev.preventDefault();
        this.call("dialog", "add", CourseTagAddDialog, {
            channelId: parseInt(ev.currentTarget.dataset.channelId, 10),
            tagIds: JSON.parse(ev.currentTarget.dataset.channelTagIds),
        });
    },
});

export default {
    websiteSlidesTag: publicWidget.registry.websiteSlidesTag,
};
