function _renderImageOnCanvas( data, formattype, rerendercallable ) {
    'use strict'
    // #1. Do NOT rely on this. No worky on IE 
    //   (url max len + lack of base64 decoder + possibly other issues)
    // #2. This does NOT affect what is captured as "signature" as far as vector data is 
    // concerned. This is treated same as "signature line" - i.e. completely ignored
    // the only time you see imported image data exported is if you export as image.

    // we do NOT call rerendercallable here (unlike in other import plugins)
    // because importing image does absolutely nothing to the underlying vector data storage
    // This could be a way to "import" old signatures stored as images
    // This could also be a way to import extra decor into signature area.

    // Odoo override: 
    // If a signature is saved in mobile resolution, when the user tries to sign a document in desktop, the size that is shown is the mobile size, which is strange for the user.
    // This modifies the library method that adds the image to the canvas, resizing the image to the canvas size.
    
    var img = new Image()
    // this = Canvas DOM elem. Not jQuery object. Not Canvas's parent div.
    , c = this;

    img.onload = function () {
        var ctx = c.getContext("2d");
        var oldShadowColor = ctx.shadowColor;
        ctx.shadowColor = "transparent";
        ctx.drawImage( 
            img, 0, 0
            , c.width
            , c.height
        );
        ctx.shadowColor = oldShadowColor;
    };

    img.src = 'data:' + formattype + ',' + data;
}

// Supported image types
const imageTypes = [
    'image',
    'image/png;base64',
    'image/jpeg;base64',
    'image/jpg;base64',
];

// Override
for (const imageType of imageTypes) {
    $.fn.jSignature("addPlugin", "import", imageType, _renderImageOnCanvas);
}
