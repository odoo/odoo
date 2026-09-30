import { Component, useSubEnv, xml } from "@odoo/owl";
import { batched } from "@web/core/utils/timing";

export class ImgGroup extends Component {
    static template = xml`<t><t t-slot="default"/></t>`;
    static props = {
        slots: Object,
    };

    setup() {
        this.load = () => {};
        this.imgProms = [];
        this.loadImgs = batched(this._loadImgs.bind(this));

        useSubEnv({
            imgGroup: {
                loaded: new Promise((resolve) => {
                    this.load = resolve;
                }),
                addImgProm: (promise) => {
                    this.imgProms.push(promise);
                    this.loadImgs();
                },
            },
        });
    }

    async _loadImgs() {
        await Promise.all(this.imgProms);
        this.load();
    }
}
