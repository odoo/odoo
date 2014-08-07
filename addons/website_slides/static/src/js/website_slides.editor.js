(function(){
    "use strict";

    var website = openerp.website;
    var _t = openerp._t;
    website.add_template_file('/website_slides/static/src/xml/website_slides.xml');

    website.EditorBarContent.include({
        new_slide: function() {
            new website.editor.AddSlideDialog().appendTo(document.body);
        },
               
    });
    website.editor.AddSlideDialog = website.editor.Dialog.extend({
        template: 'website.addslide.dialog',
        events: _.extend({}, website.editor.Dialog.prototype.events, {
            'change .slide-upload': 'slide_upload',
        }),

        start: function (){
            var r = this._super.apply(this, arguments);
            this.set_tags("");
            return r;
        },
        slide_upload: function(ev){
            var self = this;
            var file = ev.target.files[0]; 
            var fileReader = new FileReader();
            var binaryReader = new FileReader();
            fileReader.readAsArrayBuffer(file);
            binaryReader.readAsDataURL(file);
            binaryReader.onload = function FileAsBinaryOnload(evt) {
                var data = evt.target.result;
                self.file_data = data;
            };
            fileReader.onload = function FileAsArrayOnload(evt) {
                var buffer = evt.target.result;
                var uint8Array = new Uint8Array(buffer);
                // PDFJS can't eval path because of bunlde assest 
                // https://github.com/mozilla/pdf.js/blob/master/src/pdf.js#L41
                PDFJS.workerSrc = '/static/lib/pdfjs/build/pdf.worker.js';
                PDFJS.getDocument(uint8Array).then(function getPdf(pdf) {
                    pdf.getPage(1).then(function getFirstPage(page) {
                        var scale = 1;
                        var viewport = page.getViewport(scale);
                        var canvas = document.getElementById('the-canvas');
                        var context = canvas.getContext('2d');
                        canvas.height = viewport.height;
                        canvas.width = viewport.width;
                        //
                        // Render PDF page into canvas context
                        //
                        page.render({canvasContext: context, viewport: viewport});
                    });
                });
            };
        },

        set_tags: function(tags){
           this.$("input.load_tags").textext({
                plugins: 'tags focus autocomplete ajax',
                tagsItems: tags.split(","),
                // Note: The following list of keyboard keys is added. All entries are default except {32 : 'whitespace!'}.
                keys: {8: 'backspace', 9: 'tab', 13: 'enter!', 27: 'escape!', 37: 'left', 38: 'up!', 39: 'right',
                    40: 'down!', 46: 'delete', 108: 'numpadEnter', 32: 'whitespace!'},
                ajax: {
                    url: '/slides/get_tags',
                    dataType: 'json',
                    cacheResults: true
                }
            });
        },
        get_value: function(){
            var self = this;
            var values = {
                'name' : this.$('#name').val(),
                'description' : this.$('#description').val(),
                'tags' : this.$('.load_tags').textext()[0].tags()._formData,
                'file': self.file_data 
            };
            return values;
        },
        save: function () {
            var values = this.get_value();
            website.form('/slides/add_slide', 'POST', values);
        }

        });


 
})();
