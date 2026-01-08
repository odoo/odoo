/** @odoo-module **/
import { ListController } from "@web/views/list/list_controller";
import { useSetupAction } from "@web/search/action_hook";
import { useService } from "@web/core/utils/hooks";

const webListSetup = ListController.prototype.setup;

let models;
let auto_save_boolean_all;
let auto_save_boolean;

const Listsetup = function () {
    this.orm = useService("orm");

    const getListData =  async () => {
        models = await this.orm.searchRead('prevent.model.line', [], ['model']);
        auto_save_boolean_all = await this.orm.searchRead('prevent.model', [], ['auto_save_prevent_all']);
        auto_save_boolean = await this.orm.searchRead('prevent.model', [], ['auto_save_prevent']);
    }
    getListData();

    useSetupAction({
        rootRef: this.rootRef,
        beforeLeave: async () => {
            const editedRecord = this.model.root.editedRecord;
            var model_lst = models.map(dict => dict.model);
            var boolean_all_lst = auto_save_boolean_all.map(dict => dict.auto_save_prevent_all)
            var boolean_lst = auto_save_boolean.map(dict => dict.auto_save_prevent)
            if (editedRecord) {
                if (boolean_all_lst.includes(true)) {
                    this.onClickDiscard();
                    return true;
                }
                else {
                    if (model_lst.includes(this.model.root.resModel) && boolean_lst.includes(true)) {
                        this.onClickDiscard();
                        return true;
                    }
                }
            }
        },
        beforeUnload: async (ev) => {
            const editedRecord = this.model.root.editedRecord;
            var model_lst = models.map(dict => dict.model)
            var boolean_all_lst = auto_save_boolean_all.map(dict => dict.auto_save_prevent_all)
            var boolean_lst = auto_save_boolean.map(dict => dict.auto_save_prevent)
            if (editedRecord) {
                if (boolean_all_lst.includes(true)) {
                    this.onClickDiscard();
                    return true;
                } else {
                    if (model_lst.includes(this.model.root.resModel) && boolean_lst.includes(true)) {
                        this.onClickDiscard();
                        return true;
                    }
                }
            }
        },
    });
    const res = webListSetup.apply(this, arguments);
    return res;
};

ListController.prototype.setup = Listsetup;