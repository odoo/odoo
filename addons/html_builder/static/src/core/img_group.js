import { useSubEnv } from "@web/owl2/utils";
import { Component, xml, useProps, t } from "@odoo/owl";
import { batched } from "@web/core/utils/timing";

export class ImgGroup extends Component {
    static template = xml`<t><t t-call-slot="default"/></t>`;
    props = useProps({
        slots: t.object(),
    });

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
