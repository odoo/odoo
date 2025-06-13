import { MediaDialog } from "@web_editor/components/media_dialog/media_dialog";
import options from "@web_editor/js/editor/snippets.options";
import { rpc } from "@web/core/network/rpc";


options.registry.dynamic_snippet_category = options.Class.extend({
    /**
     *
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.categories = [];
    },

    async willStart() {
        const _super = this._super.bind(this);
        this.categories = await this.orm.call("product.public.category", "get_snippet_categories", []);
        return _super(...arguments);
    },

    /**
     *
     * @override
     */
    async onBuilt() {
        this.$target.get(0).dataset['columns'] = 2;
        this.$target.get(0).dataset['height'] = "small";
        this.$target.get(0).dataset['filterId'] = 0;
        this.$target.get(0).dataset['alignment'] = "left";
        this.$target.get(0).dataset['button'] = "Explore Now";
    },

    /**
     *
     * @override
     * @private
     */
    _renderCustomXML: async function (uiFragment) {
        const filtersSelectorEl = uiFragment.querySelector("[data-name='filter_opt']");
        for (let index in this.categories) {
            const category = this.categories[index]
            const button = document.createElement("we-button");
            button.dataset.selectDataAttribute = category['id'];
            button.innerText = category['name'];
            filtersSelectorEl.appendChild(button);
        }
    },
})

class categoryMedia extends MediaDialog{
    async save(){
        const nodeData = this.props.node.parentElement.dataset
        rpc('/snippets/category/set_image',{
            category_id: parseInt(nodeData.categoryId),
            media: this.selectedMedia[this.state.activeTab],
        })
        this.props.close()
        await super.save();
    }
}

options.registry.ReplaceMedia.include({
    async replaceMedia() {
        if (this.$target.closest(".s_dynamic_category").length > 0) {
            const imageEl = this.$target.get(0).querySelector(".s_category_image")
            if(this.$target.get(0).classList.contains("category_item")){
                this.call('dialog', 'add', categoryMedia, {
                    node: imageEl,
                    noDocuments: true,
                    noVideos: true,
                    noIcons: true,
                    save:() => {this.trigger_up('request_save', {
                        reload: true, optionSelector: ".s_dynamic_category"
                    })},
                })
            }else{
                await this.options.wysiwyg.openMediaDialog({
                    node: imageEl,
                    noDocuments: true,
                    noVideos: true,
                    noIcons: true,
                });
            }
        }else {
            await this._super(...arguments);
        }
    },
})


