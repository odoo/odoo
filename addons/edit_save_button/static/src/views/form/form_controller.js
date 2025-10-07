/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { Component, onWillStart, useEffect, useRef, onRendered, useState, toRaw } from "@odoo/owl";
import { useBus, useService } from "@web/core/utils/hooks";
import { useModel } from "@web/views/model";
import { SIZES } from "@web/core/ui/ui_service";

import { useViewButtons } from "@web/views/view_button/view_button_hook";
import { useSetupView } from "@web/views/view_hook";
import { useDebugCategory } from "@web/core/debug/debug_context";
import { usePager } from "@web/search/pager_hook";
import { isX2Many } from "@web/views/utils";
import { registry } from "@web/core/registry";
const viewRegistry = registry.category("views");


odoo.__DEBUG__ && console.log("Console log inside the patch function", FormController.prototype, "form_controller");

patch(FormController.prototype, "save",{
    setup() {
        this.props.preventEdit = this.env.inDialog ? false :true;
        this._super();
    },

    async edit(){
        await this._super();
        await this.model.root.switchMode("edit");
    },
    async saveButtonClicked(params = {}){
        let saved = await this._super();
        if (saved) {
        if (!this.env.inDialog) {
            await this.model.root.switchMode("readonly");
        } else {
            await this.model.actionService.doAction({ type: 'ir.actions.act_window_close' });
        }
    }
        return saved;
    },
    async discard(){
        await this._super();
        if (!this.env.inDialog){
            await this.model.root.switchMode("readonly");
        }
        else {
           this.model.actionService.doAction({type: 'ir.actions.act_window_close'});
        }
    },
     async beforeLeave() {
        if (this.model.root.isDirty) {
            if (confirm("The changes you have made will save Automatically!")) {
                return this.model.root.save({noReload: true, stayInEdition: true});
            } else {
                this.model.root.discard();
                return true;
            }
        }
     }
})

