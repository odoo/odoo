import { Component, useState } from "@odoo/owl";

import { Deferred, KeepLast } from "@web/core/utils/concurrency";
import { memoize } from "@web/core/utils/functions";

/**
 * @typedef {Object} Props
 * @property {string} src
 * @property {string} [alt]
 * @property {string} [class]
 * @property {string} [loading]
 * @property {((event: Event) => void)} [onLoad]
 * @property {((event: Event) => void)} [onClick]
 * @property {boolean} [paused]
 * @property {string} [style]
 * @extends {Component<Props, Env>}
 */
export class Gif extends Component {
    static template = "mail.Gif";
    static props = {
        src: String,
        alt: { type: String, optional: true },
        class: { type: String, optional: true },
        loading: { type: String, optional: true },
        onLoad: { type: Function, optional: true },
        onClick: { type: Function, optional: true },
        paused: { type: Boolean, optional: true },
        style: { type: String, optional: true },
    };
    static components = {};

    generateGifSnapshot = memoize(async (src) => {
        const deferred = new Deferred();
        const image = document.createElement("img");
        if (new URL(src).origin !== location.origin) {
            image.crossOrigin = "anonymous";
        }
        image.src = src;
        image.onload = () => {
            const canvas = document.createElement("canvas");
            canvas.width = image.width;
            canvas.height = image.height;
            canvas.getContext("2d").drawImage(image, 0, 0, image.width, image.height);
            deferred.resolve(canvas.toDataURL("image/gif"));
        };
        return deferred;
    });

    setup() {
        this.state = useState({ snapshot: null });
        this.keepLast = new KeepLast();
    }

    onLoad() {
        this.props.onLoad?.(...arguments);
        this.keepLast
            .add(this.generateGifSnapshot(this.props.src))
            .then((snapshot) => (this.state.snapshot = snapshot));
    }
}
