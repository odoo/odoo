/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

/**
 * Tracked translate transformations on image visualisation. This is
 * not observed for re-rendering because they are used to compute zoomer
 * style, and this is changed directly on zoomer for performance
 * reasons (overhead of making vdom is too significant for each mouse
 * position changes while dragging)
 */
registerModel({
    name: 'AttachmentViewer.Translate',
    fields: {
        dx: attr({
            default: 0,
        }),
        dy: attr({
            default: 0,
        }),
        owner: one('AttachmentViewer', {
            identifying: true,
            inverse: 'translate',
        }),
        x: attr({
            default: 0,
        }),
        y: attr({
            default: 0,
        }),
    },
});
