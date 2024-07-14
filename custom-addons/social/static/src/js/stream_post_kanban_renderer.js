/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { KanbanHeader } from '@web/views/kanban/kanban_header';
import { KanbanRenderer } from '@web/views/kanban/kanban_renderer';
import { useService } from '@web/core/utils/hooks';

import { StreamPostKanbanRecord } from './stream_post_kanban_record';
import { ImagesCarouselDialog } from './images_carousel_dialog';
import { useEffect, useRef } from "@odoo/owl";

class StreamPostKanbanHeader extends KanbanHeader {
    static template = "social.KanbanHeader";
}

export class StreamPostKanbanRenderer extends KanbanRenderer {

    setup() {
        super.setup();

        this.dialog = useService('dialog');
        const rootRef = useRef("root");
        useEffect((images) => {
            const onClickMoreImages = this.onClickMoreImages.bind(this);
            images.forEach((image) => image.addEventListener('click', onClickMoreImages));
            return () => {
                images.forEach((image) => image.removeEventListener('click', onClickMoreImages));
            };
        }, () => [rootRef.el.querySelectorAll('.o_social_stream_post_image_more')]);
    }

    /**
     * Shows a bootstrap carousel starting at the clicked image's index
     *
     * @param {PointerEvent} ev - event of the clicked image
     */
    onClickMoreImages(ev) {
        ev.stopPropagation();
        this.dialog.add(ImagesCarouselDialog, {
            title: _t("Post Images"),
            activeIndex: parseInt(ev.currentTarget.dataset.index),
            images: ev.currentTarget.dataset.imageUrls.split(',')
        })
    }

    /**
     * Always display the no-content helper, even if there are groups.
     */
    get showNoContentHelper() {
        const { model } = this.props.list;
        return !model.hasData();
    }

}

StreamPostKanbanRenderer.components = {
    ...KanbanRenderer.components,
    KanbanRecord: StreamPostKanbanRecord,
    KanbanHeader: StreamPostKanbanHeader,
};
