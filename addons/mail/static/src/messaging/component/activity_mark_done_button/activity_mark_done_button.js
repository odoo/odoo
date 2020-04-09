odoo.define('mail.messaging.component.ActivityMarkDoneButton', function (require) {
'use strict';

const components = {
    ActivityMarkDonePopover: require('mail.messaging.component.ActivityMarkDonePopover'),
    PopoverButtonWithComponent: require('mail.messaging.component.PopoverButtonWithComponent'),
};

class ActivityMarkDoneButton extends components.PopoverButtonWithComponent {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        this._onDiscardClicked = this._onDiscardClicked.bind(this);
    }

    /**
     * @override
     */
    async mounted() {
        await super.mounted();
        if (this._popoverComponent.el) {
            this._popoverComponent.el.addEventListener('o-discard-clicked', this._onDiscardClicked);
        }
    }

    /**
     * @override
     */
    willUnmount() {
        if (this._popoverComponent.el) {
            this._popoverComponent.el.removeEventListener('o-discard-clicked', this._onDiscardClicked);
        }
        super.willUnmount();
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @returns {ActivityMarkDonePopover}
     */
    _createPopoverComponent() {
        const ActivityMarkDonePopoverComponent = components.ActivityMarkDonePopover;
        ActivityMarkDonePopoverComponent.env = this.env;
        return new ActivityMarkDonePopoverComponent(null, {
            activityLocalId: this.props.activityLocalId,
        });
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onDiscardClicked(ev) {
        this._hidePopover();
    }

}

Object.assign(ActivityMarkDoneButton, {
    props: Object.assign({}, components.PopoverButtonWithComponent.props, {
        activityLocalId: String,
    }),
});

return ActivityMarkDoneButton;

});
