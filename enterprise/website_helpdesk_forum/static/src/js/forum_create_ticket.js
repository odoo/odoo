import publicWidget from "@web/legacy/js/public/public_widget";
import { CreateTicketDialog } from "../components/create_ticket_dialog/create_ticket_dialog";

publicWidget.registry.CreateTicket = publicWidget.Widget.extend({
    selector: '.create_ticket_forum',
    events: {
        'click': '_onCreateTicket',
    },

    /**
     * @override
    */
    init() {
        this._super(...arguments);
        this.dialog = this.bindService("dialog");
    },

    /**
     * @override
    */
    start() {
        this.forumId = this.$el.data('forumId');
        this.postId = this.$el.data('postId');
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _onCreateTicket() {
        this.dialog.add(CreateTicketDialog, {
            forumId: this.forumId,
            postId: this.postId,
        });
    },
});
