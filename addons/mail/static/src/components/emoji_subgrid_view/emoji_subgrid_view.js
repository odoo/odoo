/** @odoo-module **/

import { clear, insertAndReplace, replace } from '@mail/model/model_field_command';
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
            this.intervalId = setInterval(this.initializeObserver.bind(this), 10); // supposed to be after DOM painting, but refs.el are undefined?
        });

        onWillUnmount(() => {
            clearInterval(this.intervalId);
        });
    }

    initializeObserver() {
        if (!this.root.el) {
            return clear();
        }
        let options = {
            root: this.props.record.emojiGridViewOwner.component.root.el,
        };
        let observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                console.log(this.root.el);
                console.log(entry.intersectionRatio);
                /*if (entry.intersectionRatio > 0){
                    for (let i = 0; i < this.props.record.emojiGridViewOwner.emojiSubgridViews.length; i++){
                        if (this.props.record.emojiGridViewOwner.emojiSubgridViews[i] == this.props.record) {
                            this.props.record.update({ isViewedNow: true });
                            break;
                        }
                        else if (this.props.record.emojiGridViewOwner.emojiSubgridViews[i].isViewedNow) {
                            break;
                        }
                    }*/
                if (entry.intersectionRatio > 0){
                    console.log(entry.intersectionRatio);
                    console.log("Adding category: " + this.props.record.name);
                    let a = this.props.record.emojiGridViewOwner.emojiPickerViewOwner;
                    console.log(a);
                    //debugger;
                    this.props.record.update({
                        shouldNameBeSticky: true,
                        emojiPickerViewAsVisible: replace(a),
                        //emojiGridViewOwner.emojiPickerViewOwner.visibleSubgridViews: replace(this.props.record),
                    });
                    //debugger;
                    console.log("AAA" + this.props.record.emojiGridViewOwner.emojiPickerViewOwner.visibleSubgridViews);
                } else {
                    console.log("Removing category: " + this.props.record.name);
                    this.props.record.update({
                        shouldNameBeSticky: false,
                        emojiPickerViewAsVisible: clear(),
                    });
                }
            });
        }, options);
        observer.observe(this.root.el);
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
