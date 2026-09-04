/** @odoo-module */

import { ListController } from '@web/views/list/list_controller';
import { patch } from "@web/core/utils/patch";

var rpc= require('web.rpc');
patch(ListController.prototype, "DocumentListController", {
// Function to upload multiple files
   _onUploadList() {
        var self = this;
        var OnSelectedDocument = function(e) {
            for (var i = 0; i < this.files.length; i++) {
                (function(file) {
                    var selected_records = self.model.root.selection;
                    var list_ids = [];
                    for(var i=0;i<selected_records.length;i++){
                        list_ids.push(selected_records[i].resId)
                    }
                    var reader = new FileReader();
                    reader.onloadend = async function(e) {
                        var dataurl = e.target.result;
                        await rpc.query({
                            model: 'upload.multi.documents',
                            method: 'document_file_create',
                            args: [dataurl, file.name, list_ids,self.model.root.resModel],
                        }).then(function(result) {});
                    }
                    reader.readAsDataURL(file);
                })(this.files[i]);
            }
        };
        var UploadFileDocument = $('<input type="file" multiple="multiple">');
        UploadFileDocument.click();
        UploadFileDocument.on('change', OnSelectedDocument);
        },
   });
