odoo.define("test_assetsbundle.bundle4", function (require) {
    "use strict"
    require("base.ir.qweb.test_assetsbundle.bundle4");
    require("base.ir.translation.test_assetsbundle.bundle4");

    var asset_template = odoo.__DEBUG__.services['web.core'].qweb.render('test_assetsbundle');
    var template = 
        ' <div id="assetsbundle">yo yo <b>ya</b><i>yi</i> bidou</div> <pre>\n'+
        '            yep\n'+
        '            yo\n'+
        '        </pre> <div xml:space="preserve">\n'+
        '            yep\n'+
        '            gro\n'+
        '        </div> ';

    if(asset_template == template) {
        console.log('ok');
    } else {
        console.log("Wrong rendering template:\n" + '-------------' + asset_template +'-------------');
        console.log('-------------' + template +'-------------');
        console.log('error');
    }
});