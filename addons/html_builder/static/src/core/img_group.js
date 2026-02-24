import { useSubEnv } from "@web/owl2/utils";
import { Component, xml } from "@odoo/owl";
import { batched } from "@web/core/utils/timing";

export class ImgGroup extends Component {
    static template = xml`<t><t t-slot="default"/></t>`;
    static props = {
        slots: Object,
    };

    setup() {
        this.imgProms = [];
        this.loadImgs = batched(this._loadImgs.bind(this));
        this.loaded = Promise.resolve();

        useSubEnv({
            imgGroup: {
                getLoaded: () => this.loaded,
                addImgProm: (promise) => {
                    this.imgProms.push(promise);
                    this.loadImgs();
                },
            },
        });
    }

    async _loadImgs() {
        const proms = this.imgProms;
        this.imgProms = [];
        this.loaded = Promise.all(proms);
        await this.loaded;
    }
}
