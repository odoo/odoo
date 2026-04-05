/** @odoo-module **/

import {
    Component,
    onMounted,
    onWillDestroy,
    onWillUpdateProps,
    useChildSubEnv,
    useEffect,
    useState,
} from "@odoo/owl";
import { cn } from "@odx_owl/core/utils/cn";

export class Avatar extends Component {
    static template = "odx_owl.Avatar";
    static components = {};
    static props = {
        alt: { type: String, optional: true },
        className: { type: String, optional: true },
        fallback: { type: String, optional: true },
        fallbackClassName: { type: String, optional: true },
        imageClassName: { type: String, optional: true },
        slots: { type: Object, optional: true },
        src: { type: String, optional: true },
    };
    static defaultProps = {
        alt: "",
        className: "",
        fallback: "",
        fallbackClassName: "",
        imageClassName: "",
        src: "",
    };

    setup() {
        const self = this;
        this.state = useState({
            imageFailed: false,
            imageSrc: this.props.src || "",
        });

        useChildSubEnv({
            odxAvatar: {
                get alt() {
                    return self.props.alt;
                },
                get fallbackClassName() {
                    return self.props.fallbackClassName;
                },
                get imageClassName() {
                    return self.props.imageClassName;
                },
                get imageFailed() {
                    return self.state.imageFailed;
                },
                get imageSrc() {
                    return self.state.imageSrc;
                },
                hasImageSource: () => self.hasImageSource,
                markImageFailed: () => self.onImageError(),
                setImageSrc: (src) => self.setImageSrc(src),
            },
        });

        onWillUpdateProps((nextProps) => {
            if (!this.hasCustomContent && nextProps.src !== this.props.src) {
                this.setImageSrc(nextProps.src || "");
            }
        });
    }

    get hasCustomContent() {
        return Boolean(this.props.slots?.default);
    }

    get hasImageSource() {
        return Boolean(this.state.imageSrc);
    }

    get rootClasses() {
        return cn("odx-avatar", this.props.className);
    }

    get imageClasses() {
        return cn("odx-avatar__image", this.props.imageClassName);
    }

    get fallbackClasses() {
        return cn("odx-avatar__fallback", this.props.fallbackClassName);
    }

    setImageSrc(src) {
        const nextSrc = src || "";
        if (nextSrc !== this.state.imageSrc) {
            this.state.imageSrc = nextSrc;
            this.state.imageFailed = false;
        } else if (!nextSrc) {
            this.state.imageFailed = false;
        }
    }

    onImageError() {
        this.state.imageFailed = true;
    }
}

export class AvatarImage extends Component {
    static template = "odx_owl.AvatarImage";
    static props = {
        alt: { type: String, optional: true },
        className: { type: String, optional: true },
        src: { type: String, optional: true },
    };
    static defaultProps = {
        alt: "",
        className: "",
        src: "",
    };

    setup() {
        onMounted(() => this.registerSource(this.props.src));
        onWillUpdateProps((nextProps) => {
            if (nextProps.src !== this.props.src) {
                this.registerSource(nextProps.src);
            }
        });
        onWillDestroy(() => {
            if (this.props.src !== undefined) {
                this.env.odxAvatar?.setImageSrc("");
            }
        });
    }

    get alt() {
        return this.props.alt || this.env.odxAvatar?.alt || "";
    }

    get classes() {
        return cn(
            "odx-avatar__image",
            this.env.odxAvatar?.imageClassName,
            this.props.className
        );
    }

    get effectiveSrc() {
        return this.props.src || this.env.odxAvatar?.imageSrc || "";
    }

    get isVisible() {
        return Boolean(this.effectiveSrc) && !this.env.odxAvatar?.imageFailed;
    }

    registerSource(src) {
        if (src !== undefined) {
            this.env.odxAvatar?.setImageSrc(src);
        }
    }

    onError() {
        this.env.odxAvatar?.markImageFailed();
    }
}

export class AvatarFallback extends Component {
    static template = "odx_owl.AvatarFallback";
    static props = {
        className: { type: String, optional: true },
        delayMs: { type: Number, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
        text: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        delayMs: 0,
        tag: "span",
        text: "",
    };

    setup() {
        this.state = useState({
            ready: !this.props.delayMs,
        });

        useEffect(
            () => {
                if (!this.props.delayMs) {
                    this.state.ready = true;
                    return;
                }
                this.state.ready = false;
                const timer = setTimeout(() => {
                    this.state.ready = true;
                }, this.props.delayMs);
                return () => clearTimeout(timer);
            },
            () => [this.props.delayMs]
        );
    }

    get classes() {
        return cn(
            "odx-avatar__fallback",
            this.env.odxAvatar?.fallbackClassName,
            this.props.className
        );
    }

    get shouldDisplay() {
        return this.state.ready && (!this.env.odxAvatar?.hasImageSource?.() || this.env.odxAvatar?.imageFailed);
    }
}

Avatar.components = {
    AvatarFallback,
    AvatarImage,
};
