/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class Message extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
        useRefToModel({ fieldName: 'contentRef', refName: 'content' });
        useRefToModel({ fieldName: 'notificationIconRef', refName: 'notificationIcon' });
        useRefToModel({ fieldName: 'prettyBodyRef', refName: 'prettyBody' });
        useUpdateToModel({ methodName: 'onComponentUpdate' });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Tell whether the bottom of this message is visible or not.
     *
     * @param {Object} param0
     * @param {integer} [offset=0]
     * @returns {boolean}
     */
    isBottomVisible({ offset = 0 } = {}) {
        if (!this.root.el) {
            return false;
        }
        const elRect = this.root.el.getBoundingClientRect();
        if (!this.root.el.parentNode) {
            return false;
        }
        const parentRect = this.root.el.parentNode.getBoundingClientRect();
        // bottom with (double) 10px offset
        return (
            elRect.bottom < parentRect.bottom + offset &&
            parentRect.top < elRect.bottom + offset
        );
    }

    /**
     * Tell whether the message is partially visible on browser window or not.
     *
     * @returns {boolean}
     */
    isPartiallyVisible() {
        if (!this.root.el) {
            return false;
        }
        const elRect = this.root.el.getBoundingClientRect();
        if (!this.root.el.parentNode) {
            return false;
        }
        const parentRect = this.root.el.parentNode.getBoundingClientRect();
        // intersection with 5px offset
        return (
            elRect.top < parentRect.bottom + 5 &&
            parentRect.top < elRect.bottom + 5
        );
    }

    /**
     * @returns {MessageView}
     */
    get messageView() {
        return this.props.record;
    }

    /**
     * Make this message viewable in its enclosing scroll environment (usually
     * message list).
     *
     * @param {Object} [param0={}]
     * @param {string} [param0.behavior='auto']
     * @param {string} [param0.block='end']
     * @returns {Promise}
     */
    async scrollIntoView({ behavior = 'auto', block = 'end' } = {}) {
        this.root.el.scrollIntoView({
            behavior,
            block,
            inline: 'nearest',
        });
        if (behavior === 'smooth') {
            return new Promise(resolve => setTimeout(resolve, 500));
        } else {
            return Promise.resolve();
        }
    }

}

Object.assign(Message, {
    props: { record: Object },
    template: 'mail.Message',
});

registerMessagingComponent(Message);
