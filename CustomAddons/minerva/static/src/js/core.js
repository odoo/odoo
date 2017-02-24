var app = {
    domain : '/',
    fullPath: function(link){
        return app.domain + link;
    }
};

$('.back').click(function(){
    history.back();
});

$("#tabs").tabs({
    select: function(event, ui) {
        window.location.hash = ui.tab.hash;
    }
});

function loadTemplate(templatePath, templateId, callback){
    $.get(templatePath, function(template) {
        var template = $(template).filter(templateId).html();
        callback(template);
    });
}

function loadTemplateSync(templatePath, templateId){
    var templatePart;
    jQuery.ajax({
        url: templatePath,
        success: function(template) {
            templatePart = $(template).filter(templateId).html();
        },
        async: false
    });
    if (templatePart == undefined){
        throw "Can't find template ["+templatePath+templateId+"]";
    }
    return templatePart;
}

function renderTemplate(template){
    renderTemplate(template, {});
}

function renderTemplate(template, data){
    var rendered = Mustache.render(template, data);
    return rendered;
}

/*var currencyHelper = new CurrencyHelper();*/

function showAlertDialog(message, callback){
    bootbox.alert(message ? message.replace(/\n/g, "<br/>") : message, function() {
        if (callback !== undefined) {
            callback();
        }
    });
}

function showPromptDialog(message, callback){
    bootbox.prompt(message, function(result) {
        if (callback != undefined)
            callback(result);
    });
}

function showConfirmDialog(message, callback){
    bootbox.confirm(message, function(result) {
        callback(result);
    });
}

function confirmOnOKDialog(message, okCallback){
    bootbox.confirm(message, function(result) {
        if (result) {
            okCallback();
        }
    });
}

function isBrowserIE() {
    var ua = window.navigator.userAgent;
    var msie = ua.indexOf('MSIE ');
    var trident = ua.indexOf('Trident/');

    if (msie > 0) {
        // IE 10 or older => return version number
        return parseInt(ua.substring(msie + 5, ua.indexOf('.', msie)), 10);
    }

    if (trident > 0) {
        // IE 11 (or newer) => return version number
        var rv = ua.indexOf('rv:');
        return parseInt(ua.substring(rv + 3, ua.indexOf('.', rv)), 10);
    }

    // other browser
    return false;
}

function printBarcodes(skuItemIds){
    if (skuItemIds.length) {
        var query = skuItemIds.join(',');
        window.open(app.fullPath("barcode/") + query, "popupWindow");
    }
}

function applyBarcode(holder, value, options){
    $(holder).barcode(
        value,
        "code39",
        $.extend({
            barHeight: 70,
            barWidth: 1,
            showHRI: false,
            bgColor: 'transparent',
            output: 'svg'
        }, options)
    );
}

function formatDate(data, type, full) {
    return CellRenderer.dateRenderFunction(data, type, full);
}

function formatUtcDate(data, type, full) {
    return CellRenderer.dateUtcRenderFunction(data, type, full);
}

function formatTimestamp(data, type, full) {
    return CellRenderer.dateTimeRenderFunction(data, type, full);
}

function fullPath(link){
    return app.fullPath(link);
}

function isAnyModalDialogVisible() {
    return $(".modal:visible").length != 0;
}

function fillEmptyArraysWithEmptyString(obj) {
    var keys = Object.keys(obj);
    for (var i = 0; i < keys.length; i++) {
        if (Array.isArray(obj[keys[i]]) && obj[keys[i]].length <= 0) {
            obj[keys[i]] = [''];
        } else if (obj[keys[i]] instanceof Object) {
            fillEmptyArraysWithEmptyString(obj[keys[i]]);
        }
    }
    return obj;
}

function submitFormWithProgress(form) {
    var $form = $(form);
    var progressKey=Date.now();
    $form.attr("action", $form.attr("action") + '?progressKey=' + progressKey);
    Metronic.blockUI({boxed:true, message:"<div id='progressMessageId'>Processing...</div>"});
    $form.submit();
    startProgress(progressKey);
}

function runWithProgress(path, ajaxOptions) {
    var updateVar;
    function complete() {
        clearInterval(updateVar);
        Metronic.unblockUI();
    }
    Metronic.blockUI({boxed:true, message:"<div id='progressMessageId'>Processing...</div>"});
    var progressKey = path + Date.now();
    if (ajaxOptions.complete) {
        ajaxOptions.complete = [ajaxOptions.complete, complete];
    } else {
        ajaxOptions.complete = complete;
    }
    if (Array.isArray(ajaxOptions.data)) {
        ajaxOptions.data.push({
            name: 'progressKey',
            value: progressKey
        });
    } else {
        ajaxOptions.data = $.extend({}, { progressKey : progressKey}, ajaxOptions.data)
    }
    $.ajax(app.fullPath(path), ajaxOptions);
    updateVar = startProgress(progressKey);
}
function startProgress(progressKey) {
    return setInterval(function () {
        $.ajax(app.fullPath("progress"), {
            data: {progressKey: progressKey},
            dataType: 'json',
            cache: false,
            success: function (result) {
                var name = 'Processing...';
                if (result.name && result.name != null) {
                    name = result.name;
                }
                $("#progressMessageId").text(name + ' ' + result.processed + ' from ' + result.total);
            },
            error: function (data) {
                clearInterval(updateVar);
            }
        });
    }, 500);
}

function hasHorizontalScroll(element) {
    var fn = 'scrollLeft';
    return element[fn](1) && element[fn]() > 0 && element[fn](0) && true;
}

function enableDisableButton(buttonQuery, enable){
    if (enable){
        $(buttonQuery).removeAttr('disabled');
    } else {
        $(buttonQuery).attr('disabled', 'disabled');
    }
}

function customAjaxParams(){
    return {
        "type" : "POST"
    };
}

function preventDoubleClick(e)
{
    e.preventDefault();
}

var categories = [
    {"value": "0", "label": "Matematika"},
    {"value": "1", "label": "Lietuvių k."},
    {"value": "2", "label": "Rusų k."},
    {"value": "3", "label": "Anglų k."},
    {"value": "4", "label": "Antra Užsieno k."},
    {"value": "5", "label": "Istorija"},
    {"value": "6", "label": "Geografija"},
    {"value": "7", "label": "Biologija"},
    {"value": "8", "label": "Žmogaus Sauga"},
    {"value": "9", "label": "Chemija"},
    {"value": "10", "label": "Fizika"},
    {"value": "11", "label": "Dailė"},
    {"value": "12", "label": "Žodynai"},
    {"value": "13", "label": "Enciklopedijos"},
    {"value": "14", "label": "Ekonomika"},
    {"value": "15", "label": "Etika"},
    {"value": "16", "label": "Gamta ir Žmogus"},
    {"value": "17", "label": "Muzika"},
    {"value": "18", "label": "Technologijos"},
    {"value": "19", "label": "Informacinės Technologijos"},
    {"value": "20", "label": "Kita"}
];