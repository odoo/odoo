/** @odoo-module **/

import { Component } from "@odoo/owl";
import { cn } from "@odx_owl/core/utils/cn";
import { resolveDirection } from "@odx_owl/core/utils/direction";

export class Table extends Component {
    static template = "odx_owl.Table";
    static props = {
        className: { type: String, optional: true },
        dir: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        className: "",
    };

    get classes() {
        return cn("odx-table", this.props.className);
    }

    get direction() {
        return resolveDirection(this.props.dir);
    }
}

export class TableHeader extends Component {
    static template = "odx_owl.TableHeader";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        className: "",
    };

    get classes() {
        return cn("odx-table__header", this.props.className);
    }
}

export class TableBody extends Component {
    static template = "odx_owl.TableBody";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        className: "",
    };

    get classes() {
        return cn("odx-table__body", this.props.className);
    }
}

export class TableFooter extends Component {
    static template = "odx_owl.TableFooter";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        className: "",
    };

    get classes() {
        return cn("odx-table__footer", this.props.className);
    }
}

export class TableRow extends Component {
    static template = "odx_owl.TableRow";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        className: "",
    };

    get classes() {
        return cn("odx-table__row", this.props.className);
    }
}

export class TableHead extends Component {
    static template = "odx_owl.TableHead";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        className: "",
    };

    get classes() {
        return cn("odx-table__head", this.props.className);
    }
}

export class TableCell extends Component {
    static template = "odx_owl.TableCell";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        className: "",
    };

    get classes() {
        return cn("odx-table__cell", this.props.className);
    }
}

export class TableCaption extends Component {
    static template = "odx_owl.TableCaption";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        className: "",
    };

    get classes() {
        return cn("odx-table__caption", this.props.className);
    }
}
