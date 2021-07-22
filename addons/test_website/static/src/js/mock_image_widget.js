odoo.define('test_website.mock_image_widgets', function (require) {
'use strict';

const widgetsMedia = require('wysiwyg.widgets.media');

widgetsMedia.FileWidget.include({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _onFileInputChange: function () {
        function getFileFromB64(fileData) {
            const binary = atob(fileData[2]);
            let len = binary.length;
            const arr = new Uint8Array(len);
            while (len--) {
                arr[len] = binary.charCodeAt(len);
            }
            return new File([arr], fileData[1], {type: fileData[0]});
        }

        let files = [
            getFileFromB64(['image/png', 'image.png', "iVBORw0KGgoAAAANSUhEUgAAAGQAAABkCAYAAABw4pVUAAAApElEQVR42u3RAQ0AAAjDMO5fNCCDkC5z0HTVrisFCBABASIgQAQEiIAAAQJEQIAICBABASIgQAREQIAICBABASIgQAREQIAICBABASIgQAREQIAICBABASIgQAREQIAICBABASIgQAREQIAICBABASIgQAREQIAICBABASIgQAREQIAICBABASIgQAREQIAICBABASIgQAQECBAgAgJEQIAIyPcGFY7HnV2aPXoAAAAASUVORK5CYII="]),
            getFileFromB64(['image/jpeg', 'image.jpeg', "/9j/4AAQSkZJRgABAQAAAQABAAD//gAfQ29tcHJlc3NlZCBieSBqcGVnLXJlY29tcHJlc3P/2wCEAA0NDQ0ODQ4QEA4UFhMWFB4bGRkbHi0gIiAiIC1EKjIqKjIqRDxJOzc7STxsVUtLVWx9aWNpfZeHh5e+tb75+f8BDQ0NDQ4NDhAQDhQWExYUHhsZGRseLSAiICIgLUQqMioqMipEPEk7NztJPGxVS0tVbH1pY2l9l4eHl761vvn5///CABEIAEsASwMBIgACEQEDEQH/xAAVAAEBAAAAAAAAAAAAAAAAAAAABv/aAAgBAQAAAACHAAAAAAAAAAAAAAAAH//EABUBAQEAAAAAAAAAAAAAAAAAAAAH/9oACAECEAAAAKYAAAB//8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/2gAIAQMQAAAAngAAAf/EABQQAQAAAAAAAAAAAAAAAAAAAGD/2gAIAQEAAT8ASf/EABQRAQAAAAAAAAAAAAAAAAAAAED/2gAIAQIBAT8AT//EABQRAQAAAAAAAAAAAAAAAAAAAED/2gAIAQMBAT8AT//Z"]),
            getFileFromB64(['image/vnd.microsoft.icon', 'icon.ico', "AAABAAEAAQEAAAEAIAAwAAAAFgAAACgAAAABAAAAAgAAAAEAIAAAAAAABAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgAAAAA=="]),
            getFileFromB64(['image/webp', 'image.webp', "UklGRhwAAABXRUJQVlA4TBAAAAAvE8AEAAfQhuh//wMR0f8A"]),
        ];

        if (!this.options.multiImages) {
            if (this.media.classList.contains('o_mock_show_error')) {
                files = [files[2]];
            } else {
                files = [files[0]];
            }
        }
        this.$fileInput = [{'files': files}];
        return this._super(...arguments);
    }
});
});
