odoo.define('project.ProjectFormController', function (require) {
    "use strict";

    var BasicController = require('web.BasicController');
    var core = require('web.core');
    var Dialog = require('web.Dialog');
    var QWeb = core.qweb;
    var _t = core._t;

    Dialog.confirmRecurring = function (owner, message, options) {
        var buttons = [
            {
                text: _t("Ok"),
                classes: 'btn-primary',
                close: true,
                click: options && options.confirm_callback,
            },
            {
                text: _t("Cancel"),
                close: true,
                click: options && options.cancel_callback
            }
        ];
        return new Dialog(owner, _.extend({
            size: 'medium',
            buttons: buttons,
            $content: $('<main/>', {
                role: 'alert',
            }).append($('<input>', {type: 'radio', name:'recurrence_modification', id:'only', checked:true}))
            .append($('<label>', {for: 'only', text: 'This task'}))
            .append($('<br>')).append($('<input>', {type: 'radio', name:'recurrence_modification', id:'all'}))
            .append($('<label>', {for: 'all', text: 'All tasks'}))
            .append($('<br>')).append($('<input>', {type: 'radio', name:'recurrence_modification', id:'future'}))
            .append($('<label>', {for: 'future', text: 'This task and the following ones'})),
            title: message,
            onForceClose: options && (options.onForceClose || options.cancel_callback),
        }, options)).open({shouldFocusButtons:true});
    };

    var ProjectController = BasicController.extend({
    /**
     * @override
     *
     * @param {string[]} ids
     */
    _deleteRecords: function (ids) {
        var self = this;
        function doIt() {
            return self.model
                .deleteRecords(ids, self.modelName)
                .then(self._onDeletedRecords.bind(self, ids));
        }
        function doIt2() {
            let value = ""
            const array = this.$content.find('input')
            $.each(array, function(key, object){
                if (object.checked) {
                    console.log('true')
                    value = object.id
                }
            })
            switch (value) {
                case 'all':
                    console.log('get ids of all tasks linked to this recurrence');
                    var promise = self._rpc({
                        model: 'project.task',
                        method: 'get_all_tasks_from_this_recurrence',
                        args: [self.model.get(self.handle).res_id],
                    });
                    promise.then(function (result) {
                        console.log(result)
                        return self._rpc({
                            model: 'project.task',
                            method: 'unlink',
                            args: [result]
                        });
                    });
                    break;
                case 'only':
                    console.log('only this one so apply doIt()');
                    doIt();
                    break;
                case 'future':
                    console.log('get ids of all following tasks linked to this recurrence');
                    var promise = self._rpc({
                        model: self.model.get(self.handle).model,
                        method: 'get_all_following_tasks_from_this_recurrence',
                        args: [self.model.get(self.handle).res_id],
                    });
                    promise.then(function (result) {
                        console.log('res' + result)
                        // debugger;
                        // return self.model
                        //     .deleteRecords(result, self.modelName)
                        //     .then(self._onDeletedRecords.bind(self, result));
                    })
                    console.log(promise)
                    // return self.model
                    //     .deleteRecords(ids, self.modelName)
                    //     .then(self._onDeletedRecords.bind(self, ids));
                    console.log(ids)
                    break;
            }
        }
        console.log(self)
        if (self.modelName == 'project.task' && self.model.localData[ids].data.recurrency) {
            Dialog.confirmRecurring(this, _t("Delete recurring task"), {
                confirm_callback: doIt2,
            });
        }
        else if (this.confirmOnDelete) {
            Dialog.confirm(this, _t("Are you sure you want to delete this record ?"), {
                confirm_callback: doIt,
            });
        } else {
            doIt();
        }
    },
    });

    return ProjectController;
});