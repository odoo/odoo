import { Composer } from "@mail/core/common/composer";
import { onExternalClick } from "@mail/utils/common/hooks";

import { Component } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

export class RatingComposerDialog extends Component {
    static template = "portal_rating.RatingComposerDialog";
    static components = { Composer, Dialog };
    static props = ["close", "composer", "onPostCallback", "thread"];

    setup() {
        onExternalClick("root", () => this.props.close());
    }
    get title() {
        return this.props.composer.message? _t("Modify your review") : _t("Write a review");
    }

    onPostCallback() {
        this.props.onPostCallback();
        this.props.close();
    }
}
