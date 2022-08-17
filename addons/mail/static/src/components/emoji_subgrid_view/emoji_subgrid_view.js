/** @odoo-module **/

import { clear } from '@mail/model/model_field_command';
import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';

const { Component, onMounted, onWillUnmount } = owl;

export class EmojiSubgridView extends Component {
    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });

        onMounted(() => {
            this.intervalId = setInterval(this.initializeObserver.bind(this), 10); // supposed to be after DOM painting, but refs.el are still undefined for a while, so this interval makes sure the Observer is initialized at some point in the future
        });

        onWillUnmount(() => {
            clearInterval(this.intervalId);
            if (this.observer) {
                this.observer.unobserve(this.root.el);
            }
        });
    }

    initializeObserver() {
        if (!this.root.el) {
            return clear();
        }
        let options = {
            root: this.props.record.emojiGridViewOwner.component.root.el,
        };
        this.observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (entry.intersectionRatio > 0) {
                    this.props.record.update({
                        emojiPickerViewAsVisible: this.props.record.emojiGridViewOwner.emojiPickerViewOwner,
                    });
                } else {
                    this.props.record.update({
                        emojiPickerViewAsVisible: clear(),
                    });
                }
            });
        }, options);
        this.observer.observe(this.root.el);
        clearInterval(this.intervalId);
    }

    /**
     * @returns {EmojiSubgridView}
     */
    get emojiSubgridView() {
        return this.props.record;
    }
}

Object.assign(EmojiSubgridView, {
    props: { record: Object },
    template: 'mail.EmojiSubgridView',
});

registerMessagingComponent(EmojiSubgridView);
