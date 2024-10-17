import { Component } from "@odoo/owl";
import { useVisible } from "@mail/utils/common/hooks";

/**
 * @typedef {Object} Props
 * @extends {Component<Props, Env>}
 */

export class FollowerList extends Component {
    static template = "mail.FollowerList";
    static props = ["followerListView", "onClickDetails", "onClickEdit", "onClickRemove", "thread"];

    setup() {
        super.setup();
        useVisible("load-more", (isVisible) => {
            if (isVisible) {
                this.props.followerListView.loadFollowers();
            }
        });
    }

    get followersFullyLoaded() {
        return (
            this.props.followerListView.followersCount ===
            this.props.followerListView.followers.length
        );
    }
}
