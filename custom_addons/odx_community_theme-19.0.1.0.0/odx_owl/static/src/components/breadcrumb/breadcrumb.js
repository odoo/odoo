/** @odoo-module **/

import { Component, useChildSubEnv } from "@odoo/owl";
import { buttonVariants } from "@odx_owl/components/button/button";
import { cn } from "@odx_owl/core/utils/cn";
import { isRtlDirection, resolveDirection } from "@odx_owl/core/utils/direction";

export class Breadcrumb extends Component {
    static template = "odx_owl.Breadcrumb";
    static props = {
        dir: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };

    setup() {
        const self = this;
        useChildSubEnv({
            odxBreadcrumb: {
                get dir() {
                    return self.direction;
                },
            },
        });
    }

    get direction() {
        return resolveDirection(this.props.dir);
    }
}

export class BreadcrumbList extends Component {
    static template = "odx_owl.BreadcrumbList";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        className: "",
    };

    get classes() {
        return cn("odx-breadcrumb__list", this.props.className);
    }
}

export class BreadcrumbItem extends Component {
    static template = "odx_owl.BreadcrumbItem";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        className: "",
    };

    get classes() {
        return cn("odx-breadcrumb__item", this.props.className);
    }
}

export class BreadcrumbLink extends Component {
    static template = "odx_owl.BreadcrumbLink";
    static props = {
        attrs: { type: Object, optional: true },
        className: { type: String, optional: true },
        href: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        attrs: {},
        className: "",
        href: "#",
    };

    get classes() {
        return cn("odx-breadcrumb__link", this.props.className);
    }
}

export class BreadcrumbPage extends Component {
    static template = "odx_owl.BreadcrumbPage";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        className: "",
    };

    get classes() {
        return cn("odx-breadcrumb__page", this.props.className);
    }
}

export class BreadcrumbSeparator extends Component {
    static template = "odx_owl.BreadcrumbSeparator";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        className: "",
    };

    get classes() {
        return cn("odx-breadcrumb__separator", this.props.className);
    }

    get iconPath() {
        return this.env.odxBreadcrumb?.dir === "rtl"
            ? "M10 3.5L6 8L10 12.5"
            : "M6 3.5L10 8L6 12.5";
    }
}

export class BreadcrumbEllipsis extends Component {
    static template = "odx_owl.BreadcrumbEllipsis";
    static props = {
        className: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
    };

    get classes() {
        return cn("odx-breadcrumb__ellipsis", this.props.className);
    }
}

export class Pagination extends Component {
    static template = "odx_owl.Pagination";
    static props = {
        className: { type: String, optional: true },
        dir: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        className: "",
    };

    setup() {
        const self = this;
        useChildSubEnv({
            odxPagination: {
                get dir() {
                    return self.direction;
                },
            },
        });
    }

    get classes() {
        return cn("odx-pagination", this.props.className);
    }

    get direction() {
        return resolveDirection(this.props.dir);
    }
}

export class PaginationContent extends Component {
    static template = "odx_owl.PaginationContent";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        className: "",
    };

    get classes() {
        return cn("odx-pagination__content", this.props.className);
    }
}

export class PaginationItem extends Component {
    static template = "odx_owl.PaginationItem";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        className: "",
    };

    get classes() {
        return cn("odx-pagination__item", this.props.className);
    }
}

export class PaginationLink extends Component {
    static template = "odx_owl.PaginationLink";
    static props = {
        attrs: { type: Object, optional: true },
        className: { type: String, optional: true },
        href: { type: String, optional: true },
        isActive: { type: Boolean, optional: true },
        size: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        attrs: {},
        className: "",
        href: "#",
        isActive: false,
        size: "icon",
    };

    get classes() {
        return buttonVariants({
            variant: this.props.isActive ? "outline" : "ghost",
            size: this.props.size,
            className: cn("odx-pagination__link", this.props.className),
        });
    }
}

export class PaginationPrevious extends Component {
    static template = "odx_owl.PaginationPrevious";
    static props = {
        className: { type: String, optional: true },
        href: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        href: "#",
    };

    get classes() {
        return buttonVariants({
            variant: "ghost",
            size: "default",
            className: cn("odx-pagination__edge-link", this.props.className),
        });
    }

    get iconPath() {
        return isRtlDirection(this.env.odxPagination?.dir)
            ? "M6 3.5L10 8L6 12.5"
            : "M10 3.5L6 8L10 12.5";
    }
}

export class PaginationNext extends Component {
    static template = "odx_owl.PaginationNext";
    static props = {
        className: { type: String, optional: true },
        href: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        href: "#",
    };

    get classes() {
        return buttonVariants({
            variant: "ghost",
            size: "default",
            className: cn("odx-pagination__edge-link", this.props.className),
        });
    }

    get iconPath() {
        return isRtlDirection(this.env.odxPagination?.dir)
            ? "M10 3.5L6 8L10 12.5"
            : "M6 3.5L10 8L6 12.5";
    }
}

export class PaginationEllipsis extends Component {
    static template = "odx_owl.PaginationEllipsis";
    static props = {
        className: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
    };

    get classes() {
        return cn("odx-pagination__ellipsis", this.props.className);
    }
}
