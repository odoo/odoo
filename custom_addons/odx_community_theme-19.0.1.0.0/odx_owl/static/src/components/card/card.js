/** @odoo-module **/

import { Component } from "@odoo/owl";
import { cn } from "@odx_owl/core/utils/cn";

class CardBase extends Component {
    get classes() {
        return cn(this.baseClass, this.props.className);
    }
}

export class Card extends CardBase {
    static template = "odx_owl.Card";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "section",
    };
    baseClass = "odx-card";
}

export class CardHeader extends CardBase {
    static template = "odx_owl.CardHeader";
    static props = Card.props;
    static defaultProps = {
        className: "",
        tag: "div",
    };
    baseClass = "odx-card__header";
}

export class CardTitle extends CardBase {
    static template = "odx_owl.CardTitle";
    static props = Card.props;
    static defaultProps = {
        className: "",
        tag: "h3",
    };
    baseClass = "odx-card__title";
}

export class CardDescription extends CardBase {
    static template = "odx_owl.CardDescription";
    static props = Card.props;
    static defaultProps = {
        className: "",
        tag: "p",
    };
    baseClass = "odx-card__description";
}

export class CardContent extends CardBase {
    static template = "odx_owl.CardContent";
    static props = Card.props;
    static defaultProps = {
        className: "",
        tag: "div",
    };
    baseClass = "odx-card__content";
}

export class CardFooter extends CardBase {
    static template = "odx_owl.CardFooter";
    static props = Card.props;
    static defaultProps = {
        className: "",
        tag: "div",
    };
    baseClass = "odx-card__footer";
}
