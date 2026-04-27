/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { user } from "@web/core/user";
import { throttleForAnimation } from "@web/core/utils/timing";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { Component, onWillStart, useRef, useState } from "@odoo/owl";

class KnowledgeCover extends Component {
    static props = standardWidgetProps;
    static template = "knowledge.KnowledgeCover";

    setup() {
        super.setup();
        this.root = useRef("root");
        this.image = useRef("image");
        this.state = useState({
            repositioning: false,
            grabbing: false,
            // cover_image_position is false if the cover has never been repositioned before
            verticalPosition: this.props.record.data.cover_image_position || 50,
        });

        onWillStart(async () => {
            this.isInternalUser = await user.hasGroup('base.group_user');
        });

        // Update the state when we open an article (because since we open an
        // article by loading the related record, the state of this component
        // is shared between the articles and is not recomputed).
        let previousArticleId = this.props.record.resId;
        useRecordObserver((record) => {
            if (!previousArticleId || previousArticleId !== record.resId) {
                previousArticleId = record.resId;
                this.state.repositioning = false;
                this.state.grabbing = false;
                this.state.verticalPosition = record.data.cover_image_position || 50;
            }
        });
    }

    /**
     * @returns {boolean} - True if the article is editable
     */
    get isEditable() {
        const recordData = this.props.record.data;
        return !recordData.is_locked
            && recordData.user_can_write
            && recordData.active
            && this.isInternalUser;
    }

    changeCover() {
        this.env.ensureArticleName();
        this.env.openCoverSelector();
    }

    removeCover() {
        this.props.record.update({cover_image_id: false});
    }

    /**
     * Make the cover draggable so that the user can reposition it.
     */
    repositionCover() {
        this.state.repositioning = true;
        const cover = this.image.el;
        let prevPos;

        const moveCover = throttleForAnimation(ev => {
            if (prevPos !== ev.y) {
                // Add offset proportional to the distance traveled by the cursor.
                // (dividing by 5 to not move the cover too fast).
                const verticalPosition = this.state.verticalPosition + (prevPos - ev.y) / 5;
                // Make sure we are between 0.01 and 100% (not 0 since it's the
                // default value when the cover has never been repositioned).
                this.state.verticalPosition = Math.max(0.01, Math.min(100, verticalPosition));
                prevPos = ev.y;
            }
        });

        const onPointerUp = () => {
            this.state.grabbing = false;
            document.removeEventListener('pointermove', moveCover);
        };

        const onPointerDown = (ev) => {
            ev.preventDefault();
            ev.stopPropagation();
            prevPos = ev.y;
            this.state.grabbing = true;
            document.addEventListener('pointermove', moveCover);
            document.addEventListener('pointerup', onPointerUp, {once: true});
        };

        cover.addEventListener('pointerdown', onPointerDown);

        // Click outside the cover (or on save button) leaves the repositioning mode
        document.addEventListener('pointerdown', (ev) => {
            cover.removeEventListener('pointerdown', onPointerDown);
            this.state.repositioning = false;
            if (ev.target.classList.contains('o_knowledge_undo_cover_move')) {
                // Undo move
                this.state.verticalPosition = this.props.record.data.cover_image_position || 50;
            } else {
                // Save new position
                this.props.record.update({cover_image_position: this.state.verticalPosition});
            }
        }, {once: true});
    }

}

export const knowledgeCover = {
    component: KnowledgeCover,
};
registry.category("view_widgets").add("knowledge_cover", knowledgeCover);
