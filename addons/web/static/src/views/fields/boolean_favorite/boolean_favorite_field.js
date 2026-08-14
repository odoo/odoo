import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { exprToBoolean } from "@web/core/utils/strings";
import { standardFieldProps } from "../standard_field_props";

import { ANIMATION_DURATION, useAnimationMark } from "@web/core/utils/animation";
import { Component, t, useProps } from "@odoo/owl";

export class BooleanFavoriteField extends Component {
    static template = "web.BooleanFavoriteField";
    props = useProps({
        ...standardFieldProps,
        noLabel: t.boolean().optional(false),
    });

    setup() {
        super.setup();
        // Marks the click that just happened, and nothing else. `oi-filled`
        // could not: it is already there on mount, and a CSS animation replays
        // whenever its element is mounted or rebuilt.
        this.justSet = useAnimationMark(ANIMATION_DURATION.star);
    }

    get iconClass() {
        return this.props.record.data[this.props.name] ? "oi-filled" : "";
    }

    get label() {
        return this.props.record.data[this.props.name]
            ? _t("Remove from Favorites")
            : _t("Add to Favorites");
    }

    /** Kept out of `update`, which subclasses override to favorite their own way. */
    onClick() {
        // Only on the way in: unfavoriting empties the star, and there is
        // nothing being set to acknowledge.
        if (!this.props.readonly && !this.props.record.data[this.props.name]) {
            this.justSet.mark();
        }
        return this.update();
    }

    async update() {
        if (this.props.readonly) {
            return;
        }
        const changes = { [this.props.name]: !this.props.record.data[this.props.name] };
        await this.props.record.update(changes);
    }
}

export const booleanFavoriteField = {
    component: BooleanFavoriteField,
    displayName: _t("Favorite"),
    supportedTypes: ["boolean"],
    isEmpty: () => false,
    listViewWidth: ({ hasLabel }) => (!hasLabel ? 20 : false),
    extractProps: ({ attrs }, dynamicInfo) => ({
        noLabel: exprToBoolean(attrs.nolabel),
        readonly: dynamicInfo.readonly,
    }),
};

registry.category("fields").add("boolean_favorite", booleanFavoriteField);
