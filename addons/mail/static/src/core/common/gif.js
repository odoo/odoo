import { Component, props, signal, types } from "@odoo/owl";

import { KeepLast } from "@web/core/utils/concurrency";
import { memoize } from "@web/core/utils/functions";

export class Gif extends Component {
    static template = "mail.Gif";
    static components = {};

    generateGifSnapshot = memoize((src) => {
        const { promise: gifSnapshotPromise, resolve: resolveGifSnapshot } =
            Promise.withResolvers();
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
            resolveGifSnapshot(canvas.toDataURL("image/gif"));
        };
        return gifSnapshotPromise;
    });

    setup() {
        this.snapshot = signal(null);
        this.props = props({
            "alt?": types.string(),
            "class?": types.string(),
            "loading?": types.selection(["eager", "lazy"]),
            "onClick?": types.function([]),
            "onLoad?": types.function([types.instanceOf(Event)]),
            "paused?": types.boolean(),
            src: types.string(),
            "style?": types.string(),
        });
        this.keepLast = new KeepLast();
    }

    onLoad() {
        this.props.onLoad?.(...arguments);
        this.keepLast
            .add(this.generateGifSnapshot(this.props.src))
            .then((snapshot) => this.snapshot.set(snapshot));
    }
}
