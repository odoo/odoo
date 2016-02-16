odoo.define("test_assetsbundle.bundle4", function (require) {
    "use strict"
    require("base.ir.qweb.test_assetsbundle.bundle4[/test_assetsbundle/static/src/xml/assetsbundle.xml]");
    require("base.ir.translation.test_assetsbundle.bundle4");

    var asset_template = odoo.__DEBUG__.services['web.core'].qweb.render('test_assetsbundle');
    var template = '\n'+
            '        <div id="assetsbundle">yo   yo    \n'+
            '            <b>ya</b><i>yi</i> bidou</div>\n'+
            '        <pre>\n'+
            '            yep\n'+
            '            yo\n'+
            '        </pre>\n'+
            '        <div>\n'+
            '            yep\n'+
            '            gro\n'+
            '        </div>\n'+
            '    ';
    console.log(asset_template == template ? 'ok' : 'error');
});